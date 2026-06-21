"""
ScorerService — intelligent multi-factor result ranking with full explainability.

Scoring formula  (total = 100 pts):
    45 pts  semantic similarity   cosine similarity via sentence-transformers
    20 pts  source authority      platform tier + trusted-domain bonus
    15 pts  freshness             exponential time-decay from publish date
    15 pts  engagement            log-normalised across the result set
     5 pts  intent match          platform–intent alignment table

All five raw scores live in [0, 1].  Multiplying by the weight × 100 gives
the point contribution.  The sum is the final confidence (0–100).

Output per result:
    confidence       : float  — total weighted score, 0-100
    reasons          : list[str] — human-readable justifications
    _score_breakdown : dict   — per-component raw + weighted values for auditing
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


# ─────────────────────────────────────── scoring constants ───────────────────

_WEIGHTS: dict[str, float] = {
    "semantic":   0.45,
    "authority":  0.20,
    "freshness":  0.15,
    "engagement": 0.15,
    "intent":     0.05,
}

# Base authority score per platform (0-1)
_PLATFORM_AUTHORITY: dict[str, float] = {
    "Arxiv":         1.00,   # peer-reviewed preprints
    "GitHub":        0.90,   # primary source code
    "Wikipedia":     0.85,   # curated encyclopaedia
    "StackOverflow": 0.80,   # expert-verified Q&A
    "News":          0.65,   # quality varies by outlet
    "Reddit":        0.50,   # community, unverified
    "Blog":          0.40,   # fully variable quality
}
_DEFAULT_AUTHORITY = 0.50

# Domains that earn a +0.10 authority bonus (capped at 1.0)
_TRUSTED_DOMAINS: frozenset[str] = frozenset({
    # Academic / scientific publishers
    "nature.com", "science.org", "thelancet.com", "cell.com",
    "ieee.org", "acm.org", "springer.com", "sciencedirect.com",
    "plos.org", "nih.gov", "ncbi.nlm.nih.gov",
    # Elite universities
    "mit.edu", "stanford.edu", "harvard.edu", "ox.ac.uk", "cam.ac.uk",
    # Top-tier tech journalism
    "wired.com", "arstechnica.com", "techcrunch.com", "thenextweb.com",
    # Established news wire
    "reuters.com", "apnews.com", "bbc.com", "theguardian.com", "nytimes.com",
    # AI / ML orgs
    "openai.com", "deepmind.com", "anthropic.com", "huggingface.co",
    "paperswithcode.com",
})

# Per-intent, per-platform alignment score (0-1).
# Missing platform → 0.3 (neutral).
_INTENT_PLATFORM: dict[str, dict[str, float]] = {
    "coding": {
        "GitHub":        1.0,
        "StackOverflow": 1.0,
        "Arxiv":         0.4,
        "Wikipedia":     0.3,
        "Reddit":        0.5,
    },
    "research": {
        "Arxiv":         1.0,
        "Wikipedia":     0.7,
        "GitHub":        0.5,
        "StackOverflow": 0.4,
        "News":          0.3,
    },
    "news": {
        "News":          1.0,
        "Reddit":        0.6,
        "Wikipedia":     0.3,
        "GitHub":        0.2,
    },
    "comparison": {
        "Reddit":        0.8,
        "StackOverflow": 0.8,
        "Wikipedia":     0.7,
        "Arxiv":         0.5,
        "News":          0.5,
    },
    "recommendation": {
        "Reddit":        0.9,
        "StackOverflow": 0.8,
        "Wikipedia":     0.6,
        "GitHub":        0.5,
        "News":          0.4,
    },
}
_INTENT_NEUTRAL = 0.30

# Freshness: half-life in days (score = 0.5 when content is this old)
_HALF_LIFE_DAYS  = 60.0
_FRESHNESS_FLOOR = 0.10   # minimum score for very old content
_NO_DATE_SCORE   = 0.40   # neutral when no publish date is available

# Explainability thresholds
_SEM_HIGH  = 0.70
_SEM_MID   = 0.40
_AUTH_HIGH = 0.85
_AUTH_MID  = 0.65
_FRES_WEEK = 0.95    # ~< 4 days old at half_life=60
_FRES_MONTH= 0.75    # ~< 17 days old
_FRES_FAIR = 0.55    # ~< 35 days old
_ENG_HIGH  = 0.70
_ENG_MID   = 0.35
_INT_HIGH  = 0.80
_INT_MID   = 0.50


# ═══════════════════════════════════════════════════════ ScorerService ════════

class ScorerService:
    """
    Ranks search results using semantic similarity plus four structural signals.

    Integration example:
        analyzer = AnalyzerService()
        fs       = FilterService()
        scorer   = ScorerService()

        raw    = await analyzer.fetch_all("transformer architecture")
        meta   = fs.preprocess("transformer architecture")
        clean  = fs.postfilter(raw["results"], intent=meta["intent"])
        ranked = scorer.score("transformer architecture",
                              clean["results"],
                              intent=meta["intent"])
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """
        Loads the sentence-transformer model once at construction time.
        The model is ~80 MB and is cached by the HuggingFace hub on first use.
        """
        self.model = SentenceTransformer(model_name)

    # ════════════════════════════════════════════════════════════ public API ══

    def score(
        self,
        query: str,
        results: list[dict[str, Any]],
        intent: str = "research",
    ) -> list[dict[str, Any]]:
        """
        Score and rank results for a given query.

        Args:
            query:   Raw or pre-cleaned search query.
            results: List of result dicts in AnalyzerService / FilterService schema.
            intent:  Query intent string from FilterService.preprocess().

        Returns:
            All items annotated with 'confidence', 'reasons', '_score_breakdown',
            sorted by confidence descending.  No items are removed.
        """
        if not results:
            return []

        # ── batch encode: query at index 0, result texts at indices 1+ ───────
        texts = [self._result_text(r) for r in results]
        all_embeddings = self.model.encode(
            [query] + texts,
            normalize_embeddings=True,   # L2-norm → cosine = dot product
            show_progress_bar=False,
            batch_size=64,
        )
        query_emb   = all_embeddings[0]
        result_embs = all_embeddings[1:]

        # ── log-normalise engagement across the full set ──────────────────────
        max_log_eng = max(
            math.log1p(max(0, int(r.get("engagement") or 0)))
            for r in results
        ) or 1.0

        # ── score each result ─────────────────────────────────────────────────
        scored: list[dict[str, Any]] = []
        for item, emb in zip(results, result_embs):
            copy      = dict(item)
            breakdown = self._breakdown(query_emb, emb, copy, intent, max_log_eng)
            confidence = round(sum(v["weighted"] for v in breakdown.values()), 1)
            copy["confidence"]       = confidence
            copy["reasons"]          = self._explain(breakdown, copy, intent)
            copy["_score_breakdown"] = breakdown
            scored.append(copy)

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return self._diversify(scored)

    # ════════════════════════════════════════════════════════ diversity re-rank ═

    @staticmethod
    def _diversify(
        scored: list[dict[str, Any]],
        penalty_per_extra: float = 0.08,
        max_penalty_steps: int   = 4,
    ) -> list[dict[str, Any]]:
        """
        Prevent any single platform from dominating the ranked list.

        Walk results in confidence order (best-first). The first result from
        each platform keeps its score. Each subsequent result from the same
        platform loses `penalty_per_extra * 100` points per occurrence, capped
        at `max_penalty_steps` steps so very deep duplicates don't go negative.

        Example with penalty_per_extra=0.08:
          Wikipedia #1  83.1 → 83.1  (no penalty)
          Wikipedia #2  77.4 → 69.4  (−8 pts)
          Wikipedia #3  75.2 → 59.2  (−16 pts)
          Wikipedia #4  74.6 → 50.6  (−24 pts)
          Wikipedia #5+ → fixed −32 pts max

        After penalties, the list is re-sorted so higher-confidence results
        from under-represented platforms surface above penalised ones.
        """
        platform_counts: dict[str, int] = {}

        for item in scored:
            platform = (item.get("platform") or "unknown").strip()
            count    = platform_counts.get(platform, 0)

            if count > 0:
                steps   = min(count, max_penalty_steps)
                penalty = steps * penalty_per_extra * 100
                item["confidence"] = round(max(0.0, item["confidence"] - penalty), 1)
                item["reasons"].append(
                    f"diversity penalty: platform #{count + 1} ({platform})"
                )

            platform_counts[platform] = count + 1

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return scored

    # ════════════════════════════════════════════════════════════ scoring ══════

    def _breakdown(
        self,
        query_emb:  np.ndarray,
        result_emb: np.ndarray,
        item:       dict[str, Any],
        intent:     str,
        max_log_eng: float,
    ) -> dict[str, dict[str, float]]:
        """
        Compute all five sub-scores and return the weighted breakdown.

        Returns:
            {
                "semantic":   {"raw": 0.82, "weighted": 36.90},
                "authority":  {"raw": 0.90, "weighted": 18.00},
                "freshness":  {"raw": 0.75, "weighted": 11.25},
                "engagement": {"raw": 0.50, "weighted":  7.50},
                "intent":     {"raw": 1.00, "weighted":  5.00},
            }
        """
        components = {
            "semantic":   self._semantic(query_emb, result_emb),
            "authority":  self._authority(item),
            "freshness":  self._freshness(item),
            "engagement": self._engagement(item, max_log_eng),
            "intent":     self._intent(item, intent),
        }
        return {
            name: {
                "raw":      round(raw, 4),
                "weighted": round(raw * _WEIGHTS[name] * 100, 2),
            }
            for name, raw in components.items()
        }

    # ── 1. Semantic similarity ─────────────────────────────────────────────────

    @staticmethod
    def _semantic(query_emb: np.ndarray, result_emb: np.ndarray) -> float:
        """
        Cosine similarity between the query and the concatenated title+snippet.

        Because both embeddings are L2-normalised their dot product equals
        cosine similarity exactly — no division needed, O(d) per pair.

        Negative similarity (antonyms / off-topic) is clamped to 0.0 rather
        than penalising: the other factors already downweigh bad results.
        """
        return float(max(0.0, min(1.0, np.dot(query_emb, result_emb))))

    # ── 2. Source authority ────────────────────────────────────────────────────

    @staticmethod
    def _authority(item: dict[str, Any]) -> float:
        """
        Base score from the platform tier table, optionally boosted (+0.10)
        when the result's domain appears in the trusted-domain list.

        Apex-domain matching (stripping subdomains) prevents  sub.nature.com
        from escaping the boost.
        """
        platform = (item.get("platform") or "").strip()
        base     = _PLATFORM_AUTHORITY.get(platform, _DEFAULT_AUTHORITY)

        domain = (item.get("quality") or {}).get("domain", "") or ""
        apex   = re.sub(r"^(?:.*\.)?([^.]+\.[^.]+)$", r"\1", domain)
        if domain in _TRUSTED_DOMAINS or apex in _TRUSTED_DOMAINS:
            base = min(1.0, base + 0.10)

        return base

    # ── 3. Freshness ──────────────────────────────────────────────────────────

    @staticmethod
    def _freshness(item: dict[str, Any]) -> float:
        """
        Exponential half-life decay:

            score = 2^( -days_old / HALF_LIFE )

        Half-life is 60 days — content published 2 months ago scores 0.50.
        A floor of 0.10 ensures ancient but authoritative content is not
        completely nullified by the freshness factor.
        Missing or unparseable dates receive a neutral 0.40.
        """
        date_str = (item.get("date") or "").strip()
        if not date_str:
            return _NO_DATE_SCORE

        dt = ScorerService._parse_date(date_str)
        if dt is None:
            return _NO_DATE_SCORE

        now = datetime.now(tz=timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        days_old = max(0.0, (now - dt).total_seconds() / 86_400)
        raw = 2.0 ** (-days_old / _HALF_LIFE_DAYS)
        return max(_FRESHNESS_FLOOR, min(1.0, raw))

    # ── 4. Engagement ─────────────────────────────────────────────────────────

    @staticmethod
    def _engagement(item: dict[str, Any], max_log_eng: float) -> float:
        """
        Log-normalised engagement score:

            score = log(1 + eng) / log(1 + max_eng)

        Log-scale compresses the long tail of viral posts (a post with 10 000
        upvotes should not be 100× more useful than one with 100 upvotes).
        Normalising against the set maximum keeps scores in [0, 1].
        """
        eng = max(0, int(item.get("engagement") or 0))
        return math.log1p(eng) / max_log_eng

    # ── 5. Intent match ───────────────────────────────────────────────────────

    @staticmethod
    def _intent(item: dict[str, Any], intent: str) -> float:
        """
        Returns how well the result's source platform aligns with the query
        intent.  Neutral default (0.30) avoids zero-multiplying the 5 pt
        weight for platforms not listed under an intent.
        """
        platform = (item.get("platform") or "").strip()
        return _INTENT_PLATFORM.get(intent, {}).get(platform, _INTENT_NEUTRAL)

    # ════════════════════════════════════════════════════════ explainability ══

    @staticmethod
    def _explain(
        breakdown: dict[str, dict[str, float]],
        item:      dict[str, Any],
        intent:    str,
    ) -> list[str]:
        """
        Produce human-readable reason strings.

        Rules are threshold-based so reasons only appear when a component
        makes a genuinely notable contribution.  Weaknesses are surfaced too
        (e.g. "low semantic match") so the caller can understand outliers.
        """
        reasons: list[str] = []
        platform = (item.get("platform") or "").strip()
        domain   = (item.get("quality") or {}).get("domain", "") or ""
        apex     = re.sub(r"^(?:.*\.)?([^.]+\.[^.]+)$", r"\1", domain)
        trusted  = domain in _TRUSTED_DOMAINS or apex in _TRUSTED_DOMAINS

        sem  = breakdown["semantic"]["raw"]
        auth = breakdown["authority"]["raw"]
        fres = breakdown["freshness"]["raw"]
        eng  = breakdown["engagement"]["raw"]
        intn = breakdown["intent"]["raw"]

        # ── semantic ──────────────────────────────────────────────────────────
        if sem >= _SEM_HIGH:
            reasons.append("high semantic relevance")
        elif sem >= _SEM_MID:
            reasons.append("relevant to query")
        else:
            reasons.append("low semantic match")

        # ── authority ─────────────────────────────────────────────────────────
        if auth >= _AUTH_HIGH:
            tag = f"trusted platform ({platform})"
            if trusted:
                tag += f" + authoritative domain ({domain})"
            reasons.append(tag)
        elif auth >= _AUTH_MID:
            reasons.append(f"reputable source ({platform})")
        elif trusted:
            reasons.append(f"authoritative domain ({domain})")

        # ── freshness ─────────────────────────────────────────────────────────
        if fres >= _FRES_WEEK:
            reasons.append("published this week")
        elif fres >= _FRES_MONTH:
            reasons.append("published within a month")
        elif fres >= _FRES_FAIR:
            reasons.append("reasonably fresh content")
        elif fres == _NO_DATE_SCORE:
            reasons.append("publication date unknown")
        else:
            reasons.append("older content")

        # ── engagement ────────────────────────────────────────────────────────
        if eng >= _ENG_HIGH:
            reasons.append("highly engaged community")
        elif eng >= _ENG_MID:
            reasons.append("notable community engagement")

        # ── intent ────────────────────────────────────────────────────────────
        if intn >= _INT_HIGH:
            reasons.append(f"strong platform–intent fit ({intent} → {platform})")
        elif intn >= _INT_MID:
            reasons.append(f"platform suits {intent} queries")

        return reasons

    # ══════════════════════════════════════════════════════════ utilities ══════

    @staticmethod
    def _result_text(item: dict[str, Any]) -> str:
        """
        Concatenate title and snippet into one string for the encoder.
        The separator '. ' lets the model treat them as two sentences,
        which gives better embeddings than a bare space join.
        """
        title   = (item.get("title")   or "").strip()
        snippet = (item.get("snippet") or "").strip()
        if title and snippet:
            return f"{title}. {snippet}"
        return title or snippet

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """
        Parse ISO-8601 and common date strings.
        Handles the 'Z' suffix (Python < 3.11 does not accept it in fromisoformat).
        """
        cleaned = date_str.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            pass
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y",
            "%B %d, %Y",
        ):
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None


# ──────────────────────────────────────────── smoke test ─────────────────────
if __name__ == "__main__":
    from datetime import timedelta

    scorer = ScorerService()

    query  = "transformer attention mechanism neural network"
    intent = "research"

    now = datetime.now(tz=timezone.utc)

    dummy_results = [
        {
            "title":      "Attention Is All You Need",
            "snippet":    "We propose the Transformer, relying entirely on attention "
                          "to draw global dependencies between input and output.",
            "url":        "https://arxiv.org/abs/1706.03762",
            "platform":   "Arxiv",
            "date":       (now - timedelta(days=2800)).isoformat(),
            "author":     "Vaswani et al.",
            "engagement": 0,
            "quality":    {"domain": "arxiv.org", "url_valid": True,
                           "has_title": True, "has_snippet": True, "snippet_length": 120},
        },
        {
            "title":      "How to use asyncio.gather in Python",
            "snippet":    "asyncio.gather runs multiple coroutines concurrently.",
            "url":        "https://stackoverflow.com/q/12345",
            "platform":   "StackOverflow",
            "date":       (now - timedelta(days=400)).isoformat(),
            "author":     "user42",
            "engagement": 320,
            "quality":    {"domain": "stackoverflow.com", "url_valid": True,
                           "has_title": True, "has_snippet": True, "snippet_length": 55},
        },
        {
            "title":      "BERT: Pre-training of Deep Bidirectional Transformers",
            "snippet":    "We introduce BERT, designed to pre-train deep bidirectional "
                          "representations from unlabeled text by jointly conditioning "
                          "on both left and right context.",
            "url":        "https://arxiv.org/abs/1810.04805",
            "platform":   "Arxiv",
            "date":       (now - timedelta(days=2000)).isoformat(),
            "author":     "Devlin et al.",
            "engagement": 0,
            "quality":    {"domain": "arxiv.org", "url_valid": True,
                           "has_title": True, "has_snippet": True, "snippet_length": 220},
        },
        {
            "title":      "Best Python frameworks 2025",
            "snippet":    "A roundup of the most popular Python web frameworks this year.",
            "url":        "https://blog.example.com/python-2025",
            "platform":   "Blog",
            "date":       (now - timedelta(days=10)).isoformat(),
            "author":     "Blogger",
            "engagement": 45,
            "quality":    {"domain": "blog.example.com", "url_valid": True,
                           "has_title": True, "has_snippet": True, "snippet_length": 65},
        },
        {
            "title":      "Visualising Attention in Transformers",
            "snippet":    "We explore methods to visualise multi-head self-attention "
                          "weights and interpret what each head learns.",
            "url":        "https://distill.pub/visualising-attention",
            "platform":   "Arxiv",
            "date":       (now - timedelta(days=3)).isoformat(),
            "author":     "Olah et al.",
            "engagement": 890,
            "quality":    {"domain": "distill.pub", "url_valid": True,
                           "has_title": True, "has_snippet": True, "snippet_length": 140},
        },
    ]

    ranked = scorer.score(query, dummy_results, intent=intent)

    print(f"\nQuery  : '{query}'")
    print(f"Intent : {intent}")
    print("=" * 72)
    print(f"{'Rank':<5} {'Conf':>6}  {'Platform':<15} Title")
    print("-" * 72)
    for rank, r in enumerate(ranked, 1):
        title = r["title"][:40]
        print(f"  {rank:<3} {r['confidence']:>6.1f}  {r['platform']:<15} {title}")

    print("\nDetailed breakdown (top result):")
    top = ranked[0]
    print(f"  Title      : {top['title']}")
    print(f"  Confidence : {top['confidence']}")
    print(f"  Reasons    : {top['reasons']}")
    print(f"  Breakdown  :")
    for k, v in top["_score_breakdown"].items():
        bar = "█" * int(v["raw"] * 20)
        print(f"    {k:<12} raw={v['raw']:.3f}  pts={v['weighted']:>5.2f}  {bar}")
