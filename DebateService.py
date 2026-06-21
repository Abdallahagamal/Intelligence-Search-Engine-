

from __future__ import annotations

import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

_PRO_WORDS: frozenset[str] = frozenset({
    "beneficial", "effective", "superior", "promising", "breakthrough",
    "advantage", "advantages", "success", "successful", "improves",
    "improvement", "improvements", "outperforms", "achieves", "enables",
    "powerful", "robust", "efficient", "accurate", "accuracy", "best",
    "optimal", "better", "excellent", "remarkable", "significant",
    "revolutionary", "innovative", "groundbreaking", "advances", "advance",
    "surpasses", "outperform", "boosts", "boost", "excels", "excel",
    "cutting-edge", "state-of-the-art", "promising", "transformative",
    "solves", "solution", "solutions",
})

_CON_WORDS: frozenset[str] = frozenset({
    "problematic", "dangerous", "ineffective", "limited", "fails", "failure",
    "concern", "concerns", "risk", "risks", "risky", "biased", "bias",
    "harmful", "harm", "flawed", "flaw", "inadequate", "worse", "inferior",
    "poor", "unreliable", "misleading", "misinformation", "threat", "threats",
    "underperforms", "underperform", "shortcoming", "shortcomings",
    "limitation", "limitations", "overestimates", "overestimate",
    "controversial", "controversy", "problematic", "drawback", "drawbacks",
    "challenge", "challenges", "difficult", "difficulty", "obstacle",
    "obstacles", "skeptical", "skepticism", "doubt", "doubts", "uncertain",
    "uncertainty", "unreliable", "inaccurate", "insufficient",
})

_PRO_PHRASES: list[str] = [
    "we propose", "we show that", "we demonstrate", "we present",
    "state of the art", "state-of-the-art", "significant improvement",
    "outperforms", "achieves", "successfully", "promising results",
    "we introduce", "novel approach", "new approach", "we develop",
    "substantially improves", "clearly outperforms", "strong performance",
    "achieves better", "surpasses previous",
]

_CON_PHRASES: list[str] = [
    "however", "despite", "we find that it fails", "does not generalise",
    "raises serious concerns", "potential risks", "we argue against",
    "fails to", "unable to", "does not", "insufficient", "we caution",
    "critics argue", "researchers warn", "has been criticised",
    "serious limitations", "significant drawbacks", "cannot reliably",
    "shows bias", "exhibits bias", "prone to errors",
]

_CONTRAST_MARKERS: list[str] = [
    "however", "but", "yet", "although", "despite", "whereas",
    "on the other hand", "in contrast", "while some", "critics",
    "opponents", "proponents", "supporters", "nevertheless",
    "notwithstanding", "conversely",
]

_TEMPORAL_MARKERS: list[str] = [
    "traditional", "legacy", "old", "outdated", "previous", "formerly",
    "modern", "new", "recent", "latest", "current", "contemporary",
    "next-generation", "future",
]

_METHOD_MARKERS: list[str] = [
    "approach", "method", "technique", "algorithm", "framework", "model",
    "architecture", "strategy", "paradigm", "solution",
]

_HEDGE_WORDS: frozenset[str] = frozenset({
    "arguably", "generally", "typically", "often", "usually", "sometimes",
    "perhaps", "possibly", "probably", "likely", "seems", "appears",
    "suggests", "indicates", "may", "might", "could", "should",
})

_DEBATE_TYPE_SIGNALS: dict[str, list[str]] = {
    "comparison": [
        "vs", "versus", "compare", "comparison", "alternative",
        "difference", "between", "or", "which is better",
    ],
    "controversy": [
        "ethics", "ethical", "moral", "rights", "safety", "danger",
        "harmful", "threat", "policy", "regulation", "ban", "concern",
        "society", "impact", "bias", "fairness",
    ],
    "temporal": [
        "evolution", "history", "progress", "transition", "shift",
        "old", "new", "future", "emerging", "replacing", "replaced",
        "traditional", "modern", "changed",
    ],
    "methodological": [
        "approach", "technique", "method", "algorithm", "architecture",
        "framework", "pipeline", "model", "system", "implementation",
    ],
}

@dataclass
class _SourceRecord:

    title:         str
    snippet:       str
    url:           str
    platform:      str
    author:        str
    date:          str
    engagement:    int
    stance_label:  str
    stance_score:  float
    signal_words:  list[str]
    signal_phrases: list[str]
    key_claims:    list[str]
    has_contrast:  bool

@dataclass
class DebateSide:
    label:       str
    argument:    str
    stance:      str
    key_claims:  list[str]
    signal_words: list[str]
    sources:     list[dict[str, Any]]

class DebateService:

    def __init__(
        self,
        min_claim_len:       int   = 25,
        neutral_threshold:   float = 0.08,
        max_claims_per_side: int   = 6,
        max_sources_per_side: int  = 8,
    ) -> None:

        self.min_claim_len        = min_claim_len
        self.neutral_threshold    = neutral_threshold
        self.max_claims_per_side  = max_claims_per_side
        self.max_sources_per_side = max_sources_per_side

    def analyze(
        self,
        results: list[dict[str, Any]],
        topic:   str = "",
    ) -> dict[str, Any]:

        if not results:
            return self._empty_debate(topic)

        records = [self._enrich(r) for r in results]

        debate_type = self._detect_debate_type(records, topic)

        pro_recs     = [r for r in records if r.stance_label == "pro"]
        con_recs     = [r for r in records if r.stance_label == "con"]
        neutral_recs = [r for r in records if r.stance_label == "neutral"]

        if not pro_recs or not con_recs:
            pro_recs, con_recs, neutral_recs = self._rebalance(
                pro_recs, con_recs, neutral_recs
            )

        all_pro_claims = [c for r in pro_recs for c in r.key_claims]
        all_con_claims = [c for r in con_recs for c in r.key_claims]

        agreement_points    = self._find_agreements(all_pro_claims, all_con_claims)
        disagreement_points = self._find_disagreements(pro_recs, con_recs)

        side_a = self._build_side(pro_recs, "pro",  "Supporters / Pro",  debate_type)
        side_b = self._build_side(con_recs, "con",  "Critics / Con",     debate_type)

        neutral_out = {
            "sources":    [self._to_source_dict(r) for r in neutral_recs
                           [:self.max_sources_per_side]],
            "key_claims": list(dict.fromkeys(
                c for r in neutral_recs for c in r.key_claims
            ))[:self.max_claims_per_side],
        }

        intensity = self._debate_intensity(pro_recs, con_recs, disagreement_points)

        conclusion = self._build_conclusion(
            topic, side_a, side_b, agreement_points,
            disagreement_points, debate_type, intensity,
        )

        llm_ctx = self._build_llm_context(
            topic, debate_type, side_a, side_b,
            agreement_points, disagreement_points, conclusion,
        )

        return {
            "topic":               topic,
            "debate_type":         debate_type,
            "side_a":              self._side_to_dict(side_a),
            "side_b":              self._side_to_dict(side_b),
            "neutral":             neutral_out,
            "agreement_points":    agreement_points,
            "disagreement_points": disagreement_points,
            "conclusion":          conclusion,
            "debate_intensity":    round(intensity, 3),
            "llm_prompt_context":  llm_ctx,
            "metadata": {
                "total_sources":  len(results),
                "pro_count":      len(pro_recs),
                "con_count":      len(con_recs),
                "neutral_count":  len(neutral_recs),
                "debate_type":    debate_type,
                "intensity":      round(intensity, 3),
                "agreements":     len(agreement_points),
                "disagreements":  len(disagreement_points),
            },
        }

    def _enrich(self, result: dict[str, Any]) -> _SourceRecord:

        title   = _clean_text(result.get("title",   "") or "")
        snippet = _clean_text(result.get("snippet", "") or "")
        text    = f"{title}. {snippet}".lower()

        sig_words   = [w for w in _PRO_WORDS   if re.search(rf"\b{re.escape(w)}\b", text)]
        neg_words   = [w for w in _CON_WORDS   if re.search(rf"\b{re.escape(w)}\b", text)]
        sig_phrases = [p for p in _PRO_PHRASES if p in text]
        neg_phrases = [p for p in _CON_PHRASES if p in text]

        raw_score = (
            len(sig_words)   * 0.15
            - len(neg_words) * 0.15
            + len(sig_phrases) * 0.25
            - len(neg_phrases) * 0.25
        )
        score = max(-1.0, min(1.0, raw_score))

        if score > self.neutral_threshold:
            stance_label = "pro"
        elif score < -self.neutral_threshold:
            stance_label = "con"
        else:
            stance_label = "neutral"

        has_contrast = any(m in text for m in _CONTRAST_MARKERS)

        return _SourceRecord(
            title=title,
            snippet=snippet,
            url=result.get("url", "") or "",
            platform=result.get("platform", "") or "",
            author=result.get("author", "") or "",
            date=result.get("date", "") or "",
            engagement=int(result.get("engagement") or 0),
            stance_label=stance_label,
            stance_score=round(score, 4),
            signal_words=sig_words + neg_words,
            signal_phrases=sig_phrases + neg_phrases,
            key_claims=self._extract_claims(title, snippet),
            has_contrast=has_contrast,
        )

    def _extract_claims(self, title: str, snippet: str) -> list[str]:

        claims: list[str] = []

        if title and len(title) >= self.min_claim_len:
            claims.append(title)

        sentences = re.split(r"(?<=[.!?])\s+", snippet)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < self.min_claim_len:
                continue

            low = sent.lower()
            if any(re.search(rf"\b{re.escape(w)}\b", low) for w in
                   list(_PRO_WORDS)[:10] + list(_CON_WORDS)[:10]):
                if sent not in claims:
                    claims.append(sent)
            elif not claims or len(claims) == 1:

                claims.append(sent)

            if len(claims) >= 3:
                break

        return claims[:3]

    @staticmethod
    def _detect_debate_type(records: list[_SourceRecord], topic: str) -> str:

        all_text = topic.lower() + " " + " ".join(
            r.title.lower() + " " + r.snippet.lower() for r in records
        )

        type_scores: dict[str, int] = {}
        for dtype, markers in _DEBATE_TYPE_SIGNALS.items():
            score = sum(
                1 for m in markers
                if re.search(rf"\b{re.escape(m)}\b", all_text)
            )
            type_scores[dtype] = score

        priority = ["comparison", "controversy", "temporal", "methodological"]
        winner   = max(priority, key=lambda t: (type_scores.get(t, 0), -priority.index(t)))

        return winner if type_scores.get(winner, 0) > 0 else "controversy"

    @staticmethod
    def _rebalance(
        pro:     list[_SourceRecord],
        con:     list[_SourceRecord],
        neutral: list[_SourceRecord],
    ) -> tuple[list[_SourceRecord], list[_SourceRecord], list[_SourceRecord]]:

        if not neutral:
            return pro, con, neutral

        ranked = sorted(neutral, key=lambda r: r.stance_score, reverse=True)
        mid    = max(1, len(ranked) // 2)

        if not pro:
            pro     = ranked[:mid]
            neutral = ranked[mid:]
        elif not con:
            con     = ranked[mid:]
            neutral = ranked[:mid]

        return pro, con, neutral

    def _find_agreements(
        self,
        pro_claims: list[str],
        con_claims: list[str],
    ) -> list[str]:

        agreements: list[str] = []
        pro_ngrams = self._ngrams_from_claims(pro_claims)
        con_ngrams = self._ngrams_from_claims(con_claims)
        common     = pro_ngrams & con_ngrams

        already: set[str] = set()
        for pro_c in pro_claims:
            words = _tokenize(pro_c)
            for n in (3, 2):
                for i in range(len(words) - n + 1):
                    phrase = " ".join(words[i:i+n])
                    if phrase in common and phrase not in already:
                        agreements.append(phrase.capitalize())
                        already.add(phrase)
            if len(agreements) >= 4:
                break

        return agreements[:4]

    def _find_disagreements(
        self,
        pro_recs: list[_SourceRecord],
        con_recs: list[_SourceRecord],
    ) -> list[str]:

        points: list[str] = []

        pro_words = _dominant_words([c for r in pro_recs for c in r.key_claims])
        con_words = _dominant_words([c for r in con_recs for c in r.key_claims])

        shared_topics = pro_words.keys() & con_words.keys()
        for topic_word in list(shared_topics)[:3]:

            pro_context = " ".join(
                c.lower() for r in pro_recs for c in r.key_claims
                if topic_word in c.lower()
            )
            con_context = " ".join(
                c.lower() for r in con_recs for c in r.key_claims
                if topic_word in c.lower()
            )
            has_pro_sig = any(re.search(rf"\b{re.escape(w)}\b", pro_context)
                              for w in list(_PRO_WORDS)[:10])
            has_con_sig = any(re.search(rf"\b{re.escape(w)}\b", con_context)
                              for w in list(_CON_WORDS)[:10])
            if has_pro_sig and has_con_sig:
                points.append(
                    f"Opposing assessments of '{topic_word}': "
                    f"supporters highlight benefits while critics flag concerns"
                )

        pro_methods = _extract_method_mentions(pro_recs)
        con_methods = _extract_method_mentions(con_recs)
        diff_methods = pro_methods.symmetric_difference(con_methods)
        if diff_methods:
            points.append(
                "Recommended approaches diverge: "
                + " vs. ".join(list(diff_methods)[:2])
            )

        num_conflicts = self._detect_numeric_conflicts(pro_recs, con_recs)
        points.extend(num_conflicts[:2])

        return list(dict.fromkeys(points))[:5]

    @staticmethod
    def _detect_numeric_conflicts(
        pro_recs: list[_SourceRecord],
        con_recs: list[_SourceRecord],
    ) -> list[str]:

        def extract_numbers(recs: list[_SourceRecord]) -> list[tuple[str, float]]:
            out = []
            pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(%|x|times|percent|points?)", re.I)
            for r in recs:
                for sent in r.key_claims:
                    for m in pattern.finditer(sent):
                        out.append((sent[:40], float(m.group(1))))
            return out

        pro_nums = extract_numbers(pro_recs)
        con_nums = extract_numbers(con_recs)

        conflicts = []
        for pro_label, pro_val in pro_nums[:3]:
            for con_label, con_val in con_nums[:3]:

                if pro_val != 0 and abs(pro_val - con_val) / max(abs(pro_val), 1) > 0.20:
                    conflicts.append(
                        f"Numeric discrepancy: sources cite different figures "
                        f"({pro_val} vs {con_val})"
                    )
                    break
        return conflicts[:2]

    def _build_side(
        self,
        recs:       list[_SourceRecord],
        stance:     str,
        label:      str,
        debate_type: str,
    ) -> DebateSide:

        sorted_recs = sorted(
            recs,
            key=lambda r: (r.engagement, abs(r.stance_score)),
            reverse=True,
        )[:self.max_sources_per_side]

        all_claims: list[str] = []
        seen: set[str]        = set()
        for r in sorted_recs:
            for claim in r.key_claims:
                norm = claim.lower().strip()
                if norm not in seen:
                    seen.add(norm)
                    all_claims.append(claim)

        top_claims = all_claims[:self.max_claims_per_side]

        all_signals = list(dict.fromkeys(
            w for r in sorted_recs for w in r.signal_words
        ))[:8]

        argument = self._synthesise_argument(top_claims, stance, debate_type)

        return DebateSide(
            label=label,
            argument=argument,
            stance=stance,
            key_claims=top_claims,
            signal_words=all_signals,
            sources=[self._to_source_dict(r) for r in sorted_recs],
        )

    def _synthesise_argument(
        self,
        claims:     list[str],
        stance:     str,
        debate_type: str,
    ) -> str:

        if not claims:
            return "No strong claims detected for this side."

        pro_starters = [
            "Evidence suggests that",
            "Research indicates that",
            "Multiple sources confirm that",
            "It has been demonstrated that",
        ]
        con_starters = [
            "Critics argue that",
            "Concerns have been raised that",
            "Analysis reveals that",
            "A growing body of evidence suggests that",
        ]
        connectives = [
            "Furthermore,", "Additionally,", "Moreover,",
            "In support of this view,", "This is reinforced by the finding that",
        ]

        starters = pro_starters if stance == "pro" else con_starters
        parts: list[str] = []

        for i, claim in enumerate(claims[:4]):
            if i == 0:
                prefix = starters[i % len(starters)]

                first_word = (claim.split() or [""])[0]
                if first_word and not first_word.isupper():
                    claim_body = claim[0].lower() + claim[1:]
                else:
                    claim_body = claim
                parts.append(f"{prefix} {claim_body}.")
            else:
                conn = connectives[(i - 1) % len(connectives)]
                parts.append(f"{conn} {claim}.")

        return " ".join(parts)

    @staticmethod
    def _debate_intensity(
        pro_recs:   list[_SourceRecord],
        con_recs:   list[_SourceRecord],
        disagreements: list[str],
    ) -> float:

        total = len(pro_recs) + len(con_recs)
        if total == 0:
            return 0.0

        balance = 1.0 - abs(len(pro_recs) - len(con_recs)) / total

        avg_polarity = 0.0
        if pro_recs or con_recs:
            scores = [abs(r.stance_score) for r in pro_recs + con_recs]
            avg_polarity = sum(scores) / len(scores)

        disagree_bonus = min(len(disagreements) * 0.10, 0.30)

        intensity = balance * 0.40 + avg_polarity * 0.40 + disagree_bonus * 0.20
        return min(1.0, intensity)

    def _build_conclusion(
        self,
        topic:         str,
        side_a:        DebateSide,
        side_b:        DebateSide,
        agreements:    list[str],
        disagreements: list[str],
        debate_type:   str,
        intensity:     float,
    ) -> str:

        topic_str = f'on "{topic}"' if topic else "on this topic"
        n_a, n_b  = len(side_a.sources), len(side_b.sources)

        tension = (
            "sharply divided" if intensity > 0.7 else
            "moderately divided" if intensity > 0.4 else
            "nuanced"
        )

        agree_str = (
            f"Both sides agree on: {'; '.join(agreements[:2])}. "
            if agreements else ""
        )

        disagree_str = (
            f"Key points of tension include: {'; '.join(disagreements[:2])}. "
            if disagreements else ""
        )

        type_framing = {
            "comparison":     "This debate centres on a direct comparison between alternatives.",
            "controversy":    "This is an active ethical and practical controversy.",
            "temporal":       "The debate reflects a generational shift in approaches.",
            "methodological": "The disagreement is primarily methodological — different tools for the same goal.",
        }.get(debate_type, "")

        conclusion = (
            f"The evidence {topic_str} is {tension}. "
            f"{n_a} source(s) lean supportive and {n_b} source(s) raise concerns or present alternatives. "
            f"{agree_str}"
            f"{disagree_str}"
            f"{type_framing}"
        ).strip()

        return conclusion

    @staticmethod
    def _build_llm_context(
        topic:         str,
        debate_type:   str,
        side_a:        DebateSide,
        side_b:        DebateSide,
        agreements:    list[str],
        disagreements: list[str],
        conclusion:    str,
    ) -> str:

        src_block = lambda sources: "\n".join(
            f"  - [{s['platform']}] {s['title']} — {s['url']}"
            for s in sources[:4]
        ) or "  (none)"

        agree_block    = "\n".join(f"  - {a}" for a in agreements)    or "  (none identified)"
        disagree_block = "\n".join(f"  - {d}" for d in disagreements) or "  (none identified)"

        return textwrap.dedent(f"""
            === DEBATE ANALYSIS CONTEXT ===

            TOPIC        : {topic or '(unspecified)'}
            DEBATE TYPE  : {debate_type}

            --- SIDE A: {side_a.label} ---
            Stance       : {side_a.stance}
            Core argument:
              {side_a.argument}

            Key claims:
            {chr(10).join(f'  - {c}' for c in side_a.key_claims[:4])}

            Supporting sources:
            {src_block(side_a.sources)}

            --- SIDE B: {side_b.label} ---
            Stance       : {side_b.stance}
            Core argument:
              {side_b.argument}

            Key claims:
            {chr(10).join(f'  - {c}' for c in side_b.key_claims[:4])}

            Supporting sources:
            {src_block(side_b.sources)}

            --- SHARED GROUND (agreement points) ---
            {agree_block}

            --- POINTS OF CONFLICT (disagreement points) ---
            {disagree_block}

            --- PRELIMINARY CONCLUSION ---
            {conclusion}

            === END OF CONTEXT ===

            INSTRUCTIONS FOR LLM:
            Using the context above, provide:
            1. A strengthened, evidence-based argument for Side A (2-3 sentences).
            2. A strengthened, evidence-based argument for Side B (2-3 sentences).
            3. An impartial synthesis that identifies which side has stronger evidence
               and why, while acknowledging valid points from the other.
            4. One open question that this debate does not yet resolve.
        """).strip()

    @staticmethod
    def _to_source_dict(r: _SourceRecord) -> dict[str, Any]:
        return {
            "title":       r.title,
            "snippet":     r.snippet[:200],
            "url":         r.url,
            "platform":    r.platform,
            "author":      r.author,
            "date":        r.date,
            "engagement":  r.engagement,
            "stance":      r.stance_label,
            "stance_score": r.stance_score,
        }

    @staticmethod
    def _side_to_dict(side: DebateSide) -> dict[str, Any]:
        return {
            "label":       side.label,
            "argument":    side.argument,
            "stance":      side.stance,
            "key_claims":  side.key_claims,
            "signal_words": side.signal_words,
            "sources":     side.sources,
        }

    @staticmethod
    def _ngrams_from_claims(claims: list[str]) -> set[str]:
        ngrams: set[str] = set()
        for claim in claims:
            words = _tokenize(claim)
            for n in (2, 3):
                for i in range(len(words) - n + 1):
                    ngrams.add(" ".join(words[i:i+n]))
        return ngrams

    @staticmethod
    def _empty_debate(topic: str) -> dict[str, Any]:
        empty_side = {
            "label": "", "argument": "", "stance": "",
            "key_claims": [], "signal_words": [], "sources": [],
        }
        return {
            "topic": topic, "debate_type": "controversy",
            "side_a": empty_side, "side_b": empty_side,
            "neutral": {"sources": [], "key_claims": []},
            "agreement_points": [], "disagreement_points": [],
            "conclusion": "No results provided.", "debate_intensity": 0.0,
            "llm_prompt_context": "", "metadata": {},
        }

def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _tokenize(text: str) -> list[str]:

    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _HEDGE_WORDS and len(w) > 2]

def _dominant_words(claims: list[str]) -> Counter:

    skip = {"the", "a", "an", "is", "are", "was", "were", "be", "has",
            "have", "had", "that", "this", "it", "in", "of", "to",
            "for", "on", "with", "as", "by", "at", "from", "and", "or"}
    words = [
        w for claim in claims
        for w in re.findall(r"[a-z]+", claim.lower())
        if w not in skip and len(w) > 3
    ]
    return Counter(words)

def _extract_method_mentions(recs: list[_SourceRecord]) -> set[str]:

    pattern = re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:[-\s][A-Z][a-zA-Z]+)?)\b")
    methods: set[str] = set()
    for r in recs:
        for claim in r.key_claims:
            for m in pattern.findall(claim):
                if any(marker in claim.lower() for marker in _METHOD_MARKERS):
                    methods.add(m)
    return methods

if __name__ == "__main__":
    import json

    ds = DebateService()

    results = [

        {
            "title":    "AI outperforms human doctors in cancer detection study",
            "snippet":  "A landmark study demonstrates that the AI system achieves 94.5% accuracy, "
                        "significantly outperforming the 88% average of specialist physicians. "
                        "Researchers propose widespread clinical deployment to improve outcomes.",
            "url":      "https://nature.com/ai-cancer-study",
            "platform": "Arxiv", "engagement": 2400, "author": "Zhang et al.", "date": "2025-03-01",
        },
        {
            "title":    "Deep learning enables breakthrough in drug discovery",
            "snippet":  "AlphaFold successfully predicts protein structures with remarkable accuracy, "
                        "accelerating drug development pipelines and enabling novel therapies. "
                        "The approach is now adopted by over 1 000 pharmaceutical companies globally.",
            "url":      "https://deepmind.com/alphafold",
            "platform": "News", "engagement": 1800, "author": "DeepMind", "date": "2025-02-10",
        },
        {
            "title":    "GPT-4 achieves 90% accuracy on medical licensing exams",
            "snippet":  "OpenAI's GPT-4 demonstrates superior performance on the USMLE, "
                        "outperforming the average medical student score. "
                        "This promising result suggests AI can augment clinical decision making.",
            "url":      "https://openai.com/research/gpt4-medical",
            "platform": "News", "engagement": 950, "author": "OpenAI", "date": "2024-12-15",
        },

        {
            "title":    "AI diagnostic tools show dangerous racial bias, study warns",
            "snippet":  "Researchers find that AI models trained on biased datasets consistently "
                        "underperform for minority patients, raising serious ethical concerns. "
                        "Critics argue that premature deployment poses significant risks to vulnerable populations.",
            "url":      "https://thelancet.com/ai-bias-warning",
            "platform": "Arxiv", "engagement": 1600, "author": "Roberts et al.", "date": "2025-01-20",
        },
        {
            "title":    "Hospitals report failures in AI-assisted surgery systems",
            "snippet":  "Despite initial promises, several hospitals have encountered critical failures "
                        "in AI surgical assistants. Concerns have been raised about over-reliance on "
                        "ineffective models that have not been validated in real clinical environments.",
            "url":      "https://wired.com/ai-surgery-failures",
            "platform": "News", "engagement": 1100, "author": "Wired Staff", "date": "2025-03-05",
        },
        {
            "title":    "Physicians warn AI lacks contextual understanding for patient care",
            "snippet":  "A coalition of senior physicians argues that while AI shows promise on "
                        "benchmarks, it fundamentally fails to grasp patient context, cultural nuance "
                        "and the limitations of its own training data, making it unsafe for autonomous use.",
            "url":      "https://thelancet.com/physicians-warning",
            "platform": "News", "engagement": 880, "author": "Medical Council", "date": "2025-02-28",
        },

        {
            "title":    "AI in healthcare: a balanced review of evidence",
            "snippet":  "This systematic review examines 120 studies on AI clinical tools. "
                        "While some systems demonstrate measurable improvements, significant variation "
                        "in methodology makes direct comparison difficult. Standardisation is urgently needed.",
            "url":      "https://bmj.com/ai-healthcare-review",
            "platform": "Arxiv", "engagement": 700, "author": "BMJ Review Team", "date": "2025-01-05",
        },
    ]

    debate = ds.analyze(results, topic="Is AI ready to replace doctors in clinical settings?")

    print("=" * 70)
    print(f"TOPIC        : {debate['topic']}")
    print(f"DEBATE TYPE  : {debate['debate_type']}")
    print(f"INTENSITY    : {debate['debate_intensity']}  (0=mild, 1=sharp)")
    print("=" * 70)

    for key in ("side_a", "side_b"):
        side = debate[key]
        print(f"\n── {side['label'].upper()} ({len(side['sources'])} sources) ──")
        print(f"Argument     : {side['argument'][:200]}...")
        print(f"Key claims   : {side['key_claims'][:2]}")
        print(f"Signal words : {side['signal_words'][:5]}")
        print(f"Sources      :")
        for s in side["sources"][:3]:
            print(f"  [{s['platform']:<14}] {s['title'][:55]}  score={s['stance_score']}")

    print(f"\n── AGREEMENT POINTS ──")
    for pt in debate["agreement_points"] or ["(none found)"]:
        print(f"  + {pt}")

    print(f"\n── DISAGREEMENT POINTS ──")
    for pt in debate["disagreement_points"] or ["(none found)"]:
        print(f"  ✗ {pt}")

    print(f"\n── CONCLUSION ──")
    print(debate["conclusion"])

    print(f"\n── METADATA ──")
    print(json.dumps(debate["metadata"], indent=2))

    print(f"\n── LLM PROMPT CONTEXT (first 800 chars) ──")
    print(debate["llm_prompt_context"][:800])
    print("...")
