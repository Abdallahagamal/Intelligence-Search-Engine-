

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

_WEIGHTS: dict[str, float] = {
    "semantic":   0.45,
    "authority":  0.20,
    "freshness":  0.15,
    "engagement": 0.15,
    "intent":     0.05,
}

_PLATFORM_AUTHORITY: dict[str, float] = {
    "Arxiv":         1.00,
    "GitHub":        0.90,
    "Wikipedia":     0.85,
    "StackOverflow": 0.80,
    "News":          0.65,
    "Reddit":        0.50,
    "Blog":          0.40,
}
_DEFAULT_AUTHORITY = 0.50

_TRUSTED_DOMAINS: frozenset[str] = frozenset({

    "nature.com", "science.org", "thelancet.com", "cell.com",
    "ieee.org", "acm.org", "springer.com", "sciencedirect.com",
    "plos.org", "nih.gov", "ncbi.nlm.nih.gov",

    "mit.edu", "stanford.edu", "harvard.edu", "ox.ac.uk", "cam.ac.uk",

    "wired.com", "arstechnica.com", "techcrunch.com", "thenextweb.com",

    "reuters.com", "apnews.com", "bbc.com", "theguardian.com", "nytimes.com",

    "openai.com", "deepmind.com", "anthropic.com", "huggingface.co",
    "paperswithcode.com",
})

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

_HALF_LIFE_DAYS  = 60.0
_FRESHNESS_FLOOR = 0.10
_NO_DATE_SCORE   = 0.40

_SEM_HIGH  = 0.70
_SEM_MID   = 0.40
_AUTH_HIGH = 0.85
_AUTH_MID  = 0.65
_FRES_WEEK = 0.95
_FRES_MONTH= 0.75
_FRES_FAIR = 0.55
_ENG_HIGH  = 0.70
_ENG_MID   = 0.35
_INT_HIGH  = 0.80
_INT_MID   = 0.50

class ScorerService:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:

        self.model = SentenceTransformer(model_name)

    def score(
        self,
        query: str,
        results: list[dict[str, Any]],
        intent: str = "research",
    ) -> list[dict[str, Any]]:

        if not results:
            return []

        texts = [self._result_text(r) for r in results]
        all_embeddings = self.model.encode(
            [query] + texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=64,
        )
        query_emb   = all_embeddings[0]
        result_embs = all_embeddings[1:]

        max_log_eng = max(
            math.log1p(max(0, int(r.get("engagement") or 0)))
            for r in results
        ) or 1.0

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

    @staticmethod
    def _diversify(
        scored: list[dict[str, Any]],
        penalty_per_extra: float = 0.08,
        max_penalty_steps: int   = 4,
    ) -> list[dict[str, Any]]:

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

    def _breakdown(
        self,
        query_emb:  np.ndarray,
        result_emb: np.ndarray,
        item:       dict[str, Any],
        intent:     str,
        max_log_eng: float,
    ) -> dict[str, dict[str, float]]:

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

    @staticmethod
    def _semantic(query_emb: np.ndarray, result_emb: np.ndarray) -> float:

        return float(max(0.0, min(1.0, np.dot(query_emb, result_emb))))

    @staticmethod
    def _authority(item: dict[str, Any]) -> float:

        platform = (item.get("platform") or "").strip()
        base     = _PLATFORM_AUTHORITY.get(platform, _DEFAULT_AUTHORITY)

        domain = (item.get("quality") or {}).get("domain", "") or ""
        apex   = re.sub(r"^(?:.*\.)?([^.]+\.[^.]+)$", r"\1", domain)
        if domain in _TRUSTED_DOMAINS or apex in _TRUSTED_DOMAINS:
            base = min(1.0, base + 0.10)

        return base

    @staticmethod
    def _freshness(item: dict[str, Any]) -> float:

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

    @staticmethod
    def _engagement(item: dict[str, Any], max_log_eng: float) -> float:

        eng = max(0, int(item.get("engagement") or 0))
        return math.log1p(eng) / max_log_eng

    @staticmethod
    def _intent(item: dict[str, Any], intent: str) -> float:

        platform = (item.get("platform") or "").strip()
        return _INTENT_PLATFORM.get(intent, {}).get(platform, _INTENT_NEUTRAL)

    @staticmethod
    def _explain(
        breakdown: dict[str, dict[str, float]],
        item:      dict[str, Any],
        intent:    str,
    ) -> list[str]:

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

        if sem >= _SEM_HIGH:
            reasons.append("high semantic relevance")
        elif sem >= _SEM_MID:
            reasons.append("relevant to query")
        else:
            reasons.append("low semantic match")

        if auth >= _AUTH_HIGH:
            tag = f"trusted platform ({platform})"
            if trusted:
                tag += f" + authoritative domain ({domain})"
            reasons.append(tag)
        elif auth >= _AUTH_MID:
            reasons.append(f"reputable source ({platform})")
        elif trusted:
            reasons.append(f"authoritative domain ({domain})")

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

        if eng >= _ENG_HIGH:
            reasons.append("highly engaged community")
        elif eng >= _ENG_MID:
            reasons.append("notable community engagement")

        if intn >= _INT_HIGH:
            reasons.append(f"strong platform–intent fit ({intent} → {platform})")
        elif intn >= _INT_MID:
            reasons.append(f"platform suits {intent} queries")

        return reasons

    @staticmethod
    def _result_text(item: dict[str, Any]) -> str:

        title   = (item.get("title")   or "").strip()
        snippet = (item.get("snippet") or "").strip()
        if title and snippet:
            return f"{title}. {snippet}"
        return title or snippet

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:

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
