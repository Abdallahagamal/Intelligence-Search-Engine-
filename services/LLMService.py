from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_FALLBACK: dict[str, Any] = {
    "takeaway":          "insufficient evidence",
    "detailed_answer":   "insufficient evidence",
    "trends":            [],
    "related_questions": [],
    "final_conclusion":  "insufficient evidence",
}

_SYSTEM_INSTRUCTION = (
    "You are a deterministic AI research synthesis engine. "
    "Use ONLY provided sources. "
    "Output ONLY valid JSON. No extra text."
)

_RETRY_INSTRUCTION = (
    "You are a deterministic AI research synthesis engine. "
    "Use ONLY provided sources. "
    "Return ONLY valid JSON. No explanation."
)

_RESPONSE_SCHEMA = """
{
  "takeaway":          "<3-6 sentence direct answer grounded only in provided sources>",
  "detailed_answer":   "<deeper explanation merging all sources; include contradictions>",
  "trends":            ["<theme 1>", "<theme 2>", "..."],
  "related_questions": ["<question 1>", "<question 2>", "..."],
  "final_conclusion":  "<balanced synthesis; acknowledge uncertainty where present>"
}
"""

class LLMService:

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash-lite") -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "Gemini API key required. Pass api_key= or set GEMINI_API_KEY env var."
            )
        self._client = genai.Client(api_key=resolved_key)
        self._model_name = model_name

    async def generate_research_response(
        self,
        query:           str,
        ranked_sources:  list[dict[str, Any]],
        debate_results:  dict[str, Any] | None = None,
        research_graph:  dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not ranked_sources:
            return dict(_FALLBACK)

        prompt = self._build_prompt(query, ranked_sources, debate_results, research_graph)

        result = await self._call_gemini(prompt, system=_SYSTEM_INSTRUCTION)
        if result is None:
            result = await self._call_gemini(prompt, system=_RETRY_INSTRUCTION)
        if result is None:
            logger.warning("Gemini returned invalid JSON twice; using fallback.")
            return dict(_FALLBACK)

        return self._validate_and_fill(result)

    @staticmethod
    def _build_prompt(
        query:          str,
        ranked_sources: list[dict[str, Any]],
        debate_results: dict[str, Any] | None,
        research_graph: dict[str, Any] | None,
    ) -> str:
        sections: list[str] = []

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
            "- Base every claim strictly on the RANKED SOURCES above.\n"
            "- If debate_results are present, reflect both sides in detailed_answer.\n"
            "- Surface conflicts between sources; do not smooth them over.\n"
            "- If evidence is insufficient for a field, write 'insufficient evidence'.\n"
            "- Output ONLY the JSON object below. No markdown. No preamble.\n\n"
            f"REQUIRED OUTPUT SCHEMA:\n{_RESPONSE_SCHEMA}"
        )

        return "\n\n".join(sections)

    async def _call_gemini(
        self,
        prompt: str,
        system: str,
    ) -> dict[str, Any] | None:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.1,
                    top_p=0.95,
                    max_output_tokens=2048,
                ),
            )
            raw = response.text or ""
            return self._parse_json(raw)
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return None

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        raw = raw.strip()
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
