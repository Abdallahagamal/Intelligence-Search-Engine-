from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from groq import AsyncGroq

logger = logging.getLogger(__name__)

_FALLBACK: dict[str, Any] = {
    "takeaway":          "insufficient evidence",
    "detailed_answer":   "insufficient evidence",
    "trends":            [],
    "related_questions": [],
    "final_conclusion":  "insufficient evidence",
}

_SYSTEM_INSTRUCTION = (
    "You are an expert research analyst. "
    "Answer the user's question directly and concisely using ONLY the provided sources. "
    "Be specific — never vague. Output ONLY valid JSON. No extra text, no markdown fences."
)

_RETRY_INSTRUCTION = (
    "You are an expert research analyst. "
    "Answer directly using ONLY the provided sources. "
    "Return ONLY valid JSON. No explanation, no markdown, no preamble."
)

_INTENT_INSTRUCTIONS: dict[str, str] = {
    "recommendation": (
        "The user wants a CONCRETE recommendation. "
        "State clearly which option is best and when to use it. "
        "Use phrases like 'Choose X if...' or 'X is better when...'. "
        "Never be vague. Give a direct answer with reasoning."
    ),
    "comparison": (
        "Compare the options point-by-point. "
        "Be specific: performance, ecosystem, learning curve, use cases. "
        "End with a clear verdict on which is better for what."
    ),
    "coding": (
        "Focus on practical, actionable implementation details from sources. "
        "Mention specific APIs, patterns, or steps if referenced. "
        "Prioritize advice a developer can use immediately."
    ),
    "news": (
        "Report key facts precisely: dates, names, events. "
        "Distinguish confirmed facts from speculation. "
        "Prioritize the most recent and authoritative sources."
    ),
    "research": (
        "Synthesize findings across sources, noting agreements and contradictions. "
        "Cite which source supports each major claim. "
        "Highlight gaps or uncertainties in the evidence."
    ),
}

_RESPONSE_SCHEMA = """
{
  "takeaway":          "<2-4 sentences — DIRECT answer to the question, no hedging>",
  "detailed_answer":   "<comprehensive answer using all relevant sources; note contradictions>",
  "trends":            ["<specific trend 1>", "<specific trend 2>", "<specific trend 3>"],
  "related_questions": ["<follow-up question 1>", "<follow-up question 2>", "<follow-up question 3>"],
  "final_conclusion":  "<one clear, decisive conclusion the user can act on>"
}
"""

class LLMService:

    def __init__(self, api_key: str | None = None, model_name: str = "llama-3.3-70b-versatile") -> None:
        resolved_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "Groq API key required. Pass api_key= or set GROQ_API_KEY env var."
            )
        self._client = AsyncGroq(api_key=resolved_key)
        self._model_name = model_name

    async def generate_research_response(
        self,
        query:           str,
        ranked_sources:  list[dict[str, Any]],
        debate_results:  dict[str, Any] | None = None,
        research_graph:  dict[str, Any] | None = None,
        intent:          str = "research",
    ) -> dict[str, Any]:
        if not ranked_sources:
            return dict(_FALLBACK)

        prompt = self._build_prompt(query, ranked_sources, debate_results, research_graph, intent)

        result = await self._call_groq(prompt, system=_SYSTEM_INSTRUCTION)
        if result is None:
            result = await self._call_groq(prompt, system=_RETRY_INSTRUCTION)
        if result is None:
            logger.warning("Groq returned invalid JSON twice; using fallback.")
            return dict(_FALLBACK)

        return self._validate_and_fill(result)

    @staticmethod
    def _build_prompt(
        query:          str,
        ranked_sources: list[dict[str, Any]],
        debate_results: dict[str, Any] | None,
        research_graph: dict[str, Any] | None,
        intent:         str = "research",
    ) -> str:
        sections: list[str] = []

        intent_instruction = _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS["research"])
        sections.append(f"QUERY INTENT: {intent.upper()}\n{intent_instruction}")

        sections.append(f"RESEARCH QUERY:\n{query}")

        condensed_sources = [
            {
                "rank":       i + 1,
                "title":      s.get("title", ""),
                "snippet":    (s.get("snippet") or "")[:400],
                "platform":   s.get("platform", ""),
                "url":        s.get("url", ""),
                "author":     s.get("author", ""),
                "date":       s.get("date", ""),
                "engagement": s.get("engagement", 0),
                "confidence": s.get("confidence", 0),
            }
            for i, s in enumerate(ranked_sources[:15])
        ]
        sections.append(
            "RANKED SOURCES (primary truth — use ONLY these):\n"
            + json.dumps(condensed_sources, ensure_ascii=False, indent=2)
        )

        if debate_results:
            debate_condensed = {
                "topic":               debate_results.get("topic", ""),
                "debate_type":         debate_results.get("debate_type", ""),
                "debate_intensity":    debate_results.get("debate_intensity", 0),
                "side_a_argument":     (debate_results.get("side_a") or {}).get("argument", ""),
                "side_a_claims":       ((debate_results.get("side_a") or {}).get("key_claims") or [])[:3],
                "side_b_argument":     (debate_results.get("side_b") or {}).get("argument", ""),
                "side_b_claims":       ((debate_results.get("side_b") or {}).get("key_claims") or [])[:3],
                "agreement_points":    (debate_results.get("agreement_points") or [])[:3],
                "disagreement_points": (debate_results.get("disagreement_points") or [])[:3],
            }
            sections.append(
                "DEBATE ANALYSIS (show balanced perspectives; reflect conflicts):\n"
                + json.dumps(debate_condensed, ensure_ascii=False, indent=2)
            )

        if research_graph:
            top_nodes = sorted(
                [n for n in (research_graph.get("nodes") or [])
                 if n.get("data", {}).get("nodeType") not in ("query", "platform")],
                key=lambda n: n.get("data", {}).get("count", 0),
                reverse=True,
            )[:10]
            graph_condensed = {
                "top_entities": [
                    {
                        "label":    n.get("data", {}).get("label", ""),
                        "type":     n.get("data", {}).get("nodeType", ""),
                        "count":    n.get("data", {}).get("count", 0),
                        "platforms": n.get("data", {}).get("platforms", []),
                    }
                    for n in top_nodes
                ],
                "total_nodes": research_graph.get("metadata", {}).get("total_nodes", 0),
                "total_edges": research_graph.get("metadata", {}).get("total_edges", 0),
            }
            sections.append(
                "KNOWLEDGE GRAPH ENTITIES (context only — do not invent relations):\n"
                + json.dumps(graph_condensed, ensure_ascii=False, indent=2)
            )

        sections.append(
            "INSTRUCTIONS:\n"
            "- IGNORE any source whose title/snippet is clearly unrelated to the query.\n"
            "- Base every claim on RANKED SOURCES. Do not invent facts.\n"
            "- Be DIRECT and SPECIFIC. Avoid vague phrases like 'it depends' without explanation.\n"
            "- If debate_results are present, reflect both sides in detailed_answer.\n"
            "- Surface conflicts between sources; do not smooth them over.\n"
            "- trends must be specific themes (e.g. 'React dominates job market 2025'), not generic labels.\n"
            "- related_questions must be natural follow-up questions a curious user would ask.\n"
            "- Output ONLY the JSON object below. No markdown. No preamble. No <think> blocks.\n\n"
            f"REQUIRED OUTPUT SCHEMA:\n{_RESPONSE_SCHEMA}"
        )

        return "\n\n".join(sections)

    async def _call_groq(
        self,
        prompt: str,
        system: str,
    ) -> dict[str, Any] | None:
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content or ""
        logger.info("Groq raw response (%d chars): %.300s", len(raw), raw)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        raw = raw.strip()

        # Strip <think>...</think> blocks (QwQ reasoning model outputs these)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        stripped = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped).strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _validate_and_fill(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "takeaway":          str(data.get("takeaway")          or "insufficient evidence"),
            "detailed_answer":   str(data.get("detailed_answer")   or "insufficient evidence"),
            "trends":            [str(t) for t in data.get("trends",            []) if t],
            "related_questions": [str(q) for q in data.get("related_questions", []) if q],
            "final_conclusion":  str(data.get("final_conclusion")  or "insufficient evidence"),
        }
