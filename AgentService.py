

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

_INTENT_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "comparison": [
        ("vs", 2), ("versus", 2), ("compare", 2), ("comparison", 2),
        ("difference", 2), ("differences", 2), ("alternative", 1),
        ("better than", 2), ("worse than", 2), ("or", 1),
        ("pros and cons", 3), ("tradeoff", 2), ("benchmark", 2),
    ],
    "recommendation": [
        ("best", 2), ("top", 1), ("recommend", 2), ("recommended", 2),
        ("suggest", 2), ("which one", 2), ("should i use", 3),
        ("favorite", 1), ("popular", 1), ("worth", 1), ("choose", 1),
    ],
    "news": [
        ("latest", 2), ("new", 1), ("recent", 2), ("today", 2),
        ("this week", 2), ("breaking", 2), ("update", 1),
        ("announcement", 2), ("released", 1), ("2025", 1), ("2026", 1),
    ],
    "research": [
        ("paper", 2), ("papers", 2), ("research", 2), ("study", 2),
        ("survey", 2), ("arxiv", 3), ("journal", 2), ("publication", 2),
        ("experiment", 2), ("academic", 2), ("literature", 2),
        ("findings", 2), ("theory", 1), ("doi", 3),
    ],
    "coding": [
        ("how to", 2), ("implement", 2), ("function", 1), ("code", 1),
        ("library", 1), ("api", 1), ("error", 1), ("bug", 2),
        ("tutorial", 2), ("example", 1), ("install", 1), ("framework", 1),
        ("debug", 2), ("build", 1), ("deploy", 1), ("snippet", 2),
        ("programming", 1), ("algorithm", 2),
    ],
}

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "should", "may", "might", "can", "could", "i", "me", "my",
    "we", "our", "you", "your", "he", "she", "it", "its", "they",
    "their", "this", "that", "these", "those", "to", "of", "in",
    "on", "at", "by", "for", "with", "about", "from", "as", "what",
    "which", "who", "how", "all", "some", "any", "more", "so",
    "then", "very", "just", "but", "and", "or", "not", "no", "if",
    "up", "out", "use", "used", "using",
})

_SOURCE_WEIGHTS: dict[str, dict[str, float]] = {
    "research": {
        "arxiv":         0.40,
        "wikipedia":     0.20,
        "github":        0.15,
        "news":          0.10,
        "stackoverflow": 0.10,
        "reddit":        0.05,
    },
    "coding": {
        "github":        0.35,
        "stackoverflow": 0.35,
        "arxiv":         0.10,
        "wikipedia":     0.10,
        "reddit":        0.05,
        "news":          0.05,
    },
    "news": {
        "news":          0.50,
        "reddit":        0.25,
        "wikipedia":     0.10,
        "github":        0.05,
        "arxiv":         0.05,
        "stackoverflow": 0.05,
    },
    "comparison": {
        "reddit":        0.25,
        "stackoverflow": 0.25,
        "wikipedia":     0.20,
        "arxiv":         0.15,
        "news":          0.10,
        "github":        0.05,
    },
    "recommendation": {
        "reddit":        0.30,
        "stackoverflow": 0.25,
        "github":        0.20,
        "wikipedia":     0.15,
        "news":          0.05,
        "arxiv":         0.05,
    },
}

_DEFAULT_WEIGHTS: dict[str, float] = {
    "arxiv":         0.20,
    "github":        0.20,
    "wikipedia":     0.20,
    "stackoverflow": 0.15,
    "reddit":        0.15,
    "news":          0.10,
}

_PLAN_TEMPLATES: dict[str, list[dict[str, Any]]] = {

    "research": [
        {
            "phase":       "Academic Literature",
            "objective":   "Locate peer-reviewed papers, preprints, and academic surveys",
            "sources":     ["arxiv", "wikipedia"],
            "query_angle": "research paper study survey",
            "rationale":   "Academic sources provide the verified, cited foundation "
                           "for any research question",
            "priority":    "high",
        },
        {
            "phase":       "Industry Landscape",
            "objective":   "Identify how companies and practitioners apply the topic",
            "sources":     ["github", "news"],
            "query_angle": "industry application implementation trend",
            "rationale":   "Bridges the gap between theory and real-world deployment",
            "priority":    "high",
        },
        {
            "phase":       "Community Perspectives",
            "objective":   "Gather practitioner opinions and lived experience",
            "sources":     ["reddit", "stackoverflow"],
            "query_angle": "community discussion opinion experience",
            "rationale":   "Surfaces nuances and edge-cases not captured in formal writing",
            "priority":    "medium",
        },
        {
            "phase":       "Comparative Analysis",
            "objective":   "Contrast competing theories, tools, or approaches",
            "sources":     ["arxiv", "wikipedia", "reddit"],
            "query_angle": "comparison vs alternative pros cons",
            "rationale":   "Reveals trade-offs and strengthens the eventual conclusion",
            "priority":    "medium",
        },
        {
            "phase":       "Synthesis & Conclusion",
            "objective":   "Consolidate findings into a coherent, evidenced summary",
            "sources":     [],
            "query_angle": None,
            "rationale":   "Transforms raw data into an actionable research output",
            "priority":    "high",
        },
    ],

    "coding": [
        {
            "phase":       "Reference Implementations",
            "objective":   "Find authoritative code examples and open-source solutions",
            "sources":     ["github", "stackoverflow"],
            "query_angle": "code implementation example repository",
            "rationale":   "Concrete working code is the fastest path to a solution",
            "priority":    "high",
        },
        {
            "phase":       "Official Documentation",
            "objective":   "Check library docs, API references, and language specs",
            "sources":     ["wikipedia", "github"],
            "query_angle": "documentation api reference guide",
            "rationale":   "Authoritative docs prevent reliance on outdated patterns",
            "priority":    "high",
        },
        {
            "phase":       "Technical Deep-Dive",
            "objective":   "Examine underlying algorithms and design decisions",
            "sources":     ["arxiv", "stackoverflow"],
            "query_angle": "algorithm design architecture technical",
            "rationale":   "Understanding 'why' enables adapting examples to new contexts",
            "priority":    "medium",
        },
        {
            "phase":       "Community Solutions",
            "objective":   "Mine Q&A threads and discussions for edge cases and gotchas",
            "sources":     ["reddit", "stackoverflow"],
            "query_angle": "problem solution workaround issue",
            "rationale":   "Practitioners document failures that docs rarely mention",
            "priority":    "medium",
        },
        {
            "phase":       "Synthesis & Best Practice",
            "objective":   "Assemble a recommended implementation approach",
            "sources":     [],
            "query_angle": None,
            "rationale":   "Consolidates findings into a concise, actionable guide",
            "priority":    "high",
        },
    ],

    "news": [
        {
            "phase":       "Breaking & Recent Coverage",
            "objective":   "Collect the latest news articles and press releases",
            "sources":     ["news", "reddit"],
            "query_angle": "latest news announcement 2025",
            "rationale":   "Establishes the current state of affairs with primary sources",
            "priority":    "high",
        },
        {
            "phase":       "Background Context",
            "objective":   "Build factual context around the topic",
            "sources":     ["wikipedia", "arxiv"],
            "query_angle": "background history overview",
            "rationale":   "Context prevents misreading breaking news in isolation",
            "priority":    "medium",
        },
        {
            "phase":       "Community Reaction",
            "objective":   "Gauge public and expert sentiment",
            "sources":     ["reddit", "stackoverflow"],
            "query_angle": "reaction opinion impact community",
            "rationale":   "Sentiment signals which aspects matter most to stakeholders",
            "priority":    "medium",
        },
        {
            "phase":       "Trend Verification",
            "objective":   "Cross-check claims against multiple independent sources",
            "sources":     ["news", "wikipedia"],
            "query_angle": "fact check verify source",
            "rationale":   "Misinformation spreads fast; multi-source corroboration is essential",
            "priority":    "high",
        },
        {
            "phase":       "Synthesis & Timeline",
            "objective":   "Produce a verified, chronologically ordered summary",
            "sources":     [],
            "query_angle": None,
            "rationale":   "A clear timeline is the most useful output for news research",
            "priority":    "high",
        },
    ],

    "comparison": [
        {
            "phase":       "Option Discovery",
            "objective":   "Enumerate all viable options / alternatives to compare",
            "sources":     ["wikipedia", "reddit", "github"],
            "query_angle": "alternatives options list",
            "rationale":   "You cannot compare options you do not know exist",
            "priority":    "high",
        },
        {
            "phase":       "Technical Benchmarks",
            "objective":   "Gather quantitative performance and feature comparisons",
            "sources":     ["arxiv", "github", "stackoverflow"],
            "query_angle": "benchmark performance comparison test",
            "rationale":   "Objective metrics ground the comparison in measurable evidence",
            "priority":    "high",
        },
        {
            "phase":       "Real-World Usage",
            "objective":   "Understand how each option performs in production",
            "sources":     ["reddit", "stackoverflow", "news"],
            "query_angle": "production usage real world experience",
            "rationale":   "Benchmark results and production reality often diverge",
            "priority":    "medium",
        },
        {
            "phase":       "Pros & Cons Synthesis",
            "objective":   "Build a structured trade-off matrix for each option",
            "sources":     [],
            "query_angle": None,
            "rationale":   "Decision-makers need a concise, structured artefact",
            "priority":    "high",
        },
    ],

    "recommendation": [
        {
            "phase":       "Requirements & Criteria",
            "objective":   "Identify the key needs the recommendation must satisfy",
            "sources":     ["reddit", "stackoverflow"],
            "query_angle": "criteria requirements choose when to use",
            "rationale":   "A recommendation without stated criteria cannot be evaluated",
            "priority":    "high",
        },
        {
            "phase":       "Top Options Survey",
            "objective":   "Find the most frequently recommended candidates",
            "sources":     ["reddit", "stackoverflow", "github"],
            "query_angle": "best recommended top popular",
            "rationale":   "Community wisdom surfaces battle-tested options quickly",
            "priority":    "high",
        },
        {
            "phase":       "Technical Validation",
            "objective":   "Verify candidate quality against objective signals",
            "sources":     ["github", "arxiv"],
            "query_angle": "stars activity maintained quality",
            "rationale":   "Popularity alone does not guarantee suitability or quality",
            "priority":    "medium",
        },
        {
            "phase":       "Community Sentiment",
            "objective":   "Validate recommendations with real user experience",
            "sources":     ["reddit", "news"],
            "query_angle": "review user experience sentiment opinion",
            "rationale":   "Negative patterns (bugs, poor DX) surface in community threads",
            "priority":    "medium",
        },
        {
            "phase":       "Final Recommendation",
            "objective":   "Produce a ranked, justified shortlist",
            "sources":     [],
            "query_angle": None,
            "rationale":   "The output must be directly actionable for the end user",
            "priority":    "high",
        },
    ],
}

_DEFAULT_TEMPLATE = _PLAN_TEMPLATES["research"]

_STRATEGY_NAMES: dict[str, str] = {
    "research":       "academic_first",
    "coding":         "solution_first",
    "news":           "recency_first",
    "comparison":     "breadth_first",
    "recommendation": "community_first",
}

_TEMPORAL_MODIFIERS: dict[str, str] = {
    "research":       "2024 2025",
    "coding":         "",
    "news":           "latest 2025 recent",
    "comparison":     "",
    "recommendation": "2025",
}

class ResearchAgent:

    def plan(self, question: str) -> dict[str, Any]:

        cleaned  = self._clean(question)
        lower    = cleaned.lower()
        keywords = self._extract_keywords(lower)

        intent, confidence = self._detect_intent(lower)

        weights   = _SOURCE_WEIGHTS.get(intent, _DEFAULT_WEIGHTS)
        template  = _PLAN_TEMPLATES.get(intent, _DEFAULT_TEMPLATE)
        strategy  = _STRATEGY_NAMES.get(intent, "breadth_first")
        variants  = self._query_variants(cleaned, keywords, intent)

        steps = self._build_steps(template, keywords, intent)

        active = sorted({s for step in steps for s in step["sources"]})

        query_steps      = sum(1 for s in steps if s["query"] is not None)
        estimated_results = len(active) * 10 * max(query_steps, 1)

        return {
            "question":           question,
            "cleaned_question":   cleaned,
            "intent":             intent,
            "intent_confidence":  round(confidence, 3),
            "keywords":           keywords,
            "query_variants":     variants,
            "source_weights":     weights,
            "strategy":           strategy,
            "steps":              steps,
            "active_sources":     active,
            "estimated_results":  estimated_results,
            "created_at":         datetime.now(tz=timezone.utc).isoformat(),
        }

    def describe(self, plan: dict[str, Any]) -> str:

        lines: list[str] = [
            f"Research Plan",
            f"{'─' * 60}",
            f"Question  : {plan['question']}",
            f"Intent    : {plan['intent']}  (confidence={plan['intent_confidence']})",
            f"Strategy  : {plan['strategy']}",
            f"Keywords  : {', '.join(plan['keywords'][:8])}",
            f"Variants  : {len(plan['query_variants'])} query angles",
            f"Sources   : {', '.join(plan['active_sources'])}",
            f"Est. hits : ~{plan['estimated_results']}",
            f"",
            f"Source weights:",
        ]
        for src, w in sorted(plan["source_weights"].items(), key=lambda x: -x[1]):
            bar = "█" * int(w * 30)
            lines.append(f"  {src:<15} {w:.0%}  {bar}")

        lines += ["", "Steps:"]
        for step in plan["steps"]:
            src_str = ", ".join(step["sources"]) if step["sources"] else "— (internal synthesis)"
            q_str   = f'"{step["query"]}"' if step["query"] else "—"
            lines += [
                f"  {step['step_id']}. [{step['priority'].upper():6}] {step['phase']}",
                f"     Objective : {step['objective']}",
                f"     Sources   : {src_str}",
                f"     Query     : {q_str}",
                f"     Rationale : {step['rationale']}",
                "",
            ]
        return "\n".join(lines)

    @staticmethod
    def _clean(text: str) -> str:
        text = unicodedata.normalize("NFKC", text.strip())
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        for src, dst in (("'", "'"), ("'", "'"), ("“", '"'), ("”", '"'),
                         ("–", "-"), ("—", "-")):
            text = text.replace(src, dst)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        tokens = re.sub(r"[^\w\s]", " ", text).split()
        return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]

    @staticmethod
    def _detect_intent(text: str) -> tuple[str, float]:

        scores: dict[str, int] = {k: 0 for k in _INTENT_SIGNALS}
        for intent, signals in _INTENT_SIGNALS.items():
            for signal, weight in signals:
                if " " in signal:
                    if signal in text:
                        scores[intent] += weight
                else:
                    if re.search(r"\b" + re.escape(signal) + r"\b", text):
                        scores[intent] += weight

        priority = ["comparison", "recommendation", "news", "research", "coding"]
        best = max(priority, key=lambda i: (scores[i], -priority.index(i)))

        if scores[best] == 0:
            return "research", 0.0

        return best, scores[best] / (sum(scores.values()) or 1)

    @staticmethod
    def _query_variants(
        cleaned: str,
        keywords: list[str],
        intent: str,
    ) -> list[str]:

        variants: list[str] = []
        kw_core = " ".join(keywords[:5])
        temporal = _TEMPORAL_MODIFIERS.get(intent, "")

        intent_mods: dict[str, list[str]] = {
            "research":       ["research analysis", "academic study"],
            "coding":         ["implementation tutorial", "code example"],
            "news":           ["latest news", "recent update"],
            "comparison":     ["comparison vs alternative", "pros cons"],
            "recommendation": ["best recommended", "top picks"],
        }

        sub_aspects: dict[str, str] = {
            "research":       "challenges limitations future directions",
            "coding":         "best practices common errors",
            "news":           "impact implications consequences",
            "comparison":     "performance benchmark real world",
            "recommendation": "beginner advanced use case",
        }

        candidates = [
            cleaned,
            kw_core,
        ]
        for mod in intent_mods.get(intent, [])[:2]:
            if kw_core:
                candidates.append(f"{kw_core} {mod}")
        if temporal and kw_core:
            candidates.append(f"{kw_core} {temporal}")
        aspect = sub_aspects.get(intent, "")
        if aspect and kw_core:
            candidates.append(f"{kw_core} {aspect}")

        seen: set[str] = set()
        for c in candidates:
            c = c.strip()
            if c and c not in seen:
                seen.add(c)
                variants.append(c)
            if len(variants) == 5:
                break

        return variants

    @staticmethod
    def _build_steps(
        template: list[dict[str, Any]],
        keywords: list[str],
        intent:   str,
    ) -> list[dict[str, Any]]:

        steps: list[dict[str, Any]] = []
        kw_base = " ".join(keywords[:4]) if keywords else ""

        for i, tpl in enumerate(template, start=1):
            angle = tpl.get("query_angle")
            if angle and kw_base:
                query: str | None = f"{kw_base} {angle}".strip()
            elif angle:
                query = angle
            else:
                query = None

            steps.append({
                "step_id":   i,
                "phase":     tpl["phase"],
                "objective": tpl["objective"],
                "sources":   list(tpl["sources"]),
                "query":     query,
                "rationale": tpl["rationale"],
                "priority":  tpl["priority"],
            })

        return steps

if __name__ == "__main__":
    agent = ResearchAgent()

    questions = [
        "What is the future of AI?",
        "How do I implement a transformer from scratch in PyTorch?",
        "Latest GPT-5 news 2025",
        "React vs Vue vs Svelte for a large SPA",
        "Best vector database for production RAG pipelines",
    ]

    for q in questions:
        plan = agent.plan(q)
        print()
        print(agent.describe(plan))
        print("─" * 60)
