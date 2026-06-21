

from __future__ import annotations

import json
import math
import sys
import time
import traceback
from pathlib import Path
from typing import Any

_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

GREEN  = lambda t: _c("32", t)
RED    = lambda t: _c("31", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)

_SUITES: dict[str, tuple[type, list[tuple[str, str]]]] = {}
_VERBOSE: bool = "-v" in sys.argv

def suite(name: str):

    def decorator(cls):
        methods = [
            (attr.replace("test_", "", 1).replace("_", " "), attr)
            for attr in sorted(dir(cls))
            if attr.startswith("test_")
        ]
        _SUITES[name] = (cls, methods)
        return cls
    return decorator

def fail(msg: str) -> None:
    raise AssertionError(msg)

def assert_eq(actual, expected, label: str = "") -> None:
    if actual != expected:
        fail(f"{label}: expected {expected!r}, got {actual!r}")

def assert_in(item, container, label: str = "") -> None:
    if item not in container:
        fail(f"{label}: {item!r} not in {container!r}")

def assert_type(value, typ, label: str = "") -> None:
    if not isinstance(value, typ):
        fail(f"{label}: expected {typ.__name__}, got {type(value).__name__}")

def assert_range(value: float, lo: float, hi: float, label: str = "") -> None:
    if not (lo <= value <= hi):
        fail(f"{label}: {value} not in [{lo}, {hi}]")

def assert_keys(d: dict, keys: list[str], label: str = "") -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        fail(f"{label}: missing keys {missing}")

_ROOT = Path(__file__).parent
_DUMMY_PATH = _ROOT / "Dummy.json"
_QUERY = "How do I start learning machine learning in 2026?"

_PLATFORM_MAP = {"reddit": "Reddit", "github": "GitHub", "arxiv": "Arxiv"}

def _load_dummy() -> list[dict[str, Any]]:

    raw: list[dict] = json.loads(_DUMMY_PATH.read_text())
    results = []
    for item in raw:
        src = item.get("source", "unknown")
        engagement = (
            item.get("upvotes") or
            item.get("stars")   or
            item.get("citations") or 0
        )
        results.append({
            "title":      item.get("title", ""),
            "snippet":    item.get("content", ""),
            "url":        f"https://example.com/{src}/{item['id']}",
            "platform":   _PLATFORM_MAP.get(src, src.capitalize()),
            "date":       "2025-03-15T10:00:00Z",
            "author":     "test_user",
            "engagement": int(engagement),
        })
    return results

DUMMY_RESULTS = _load_dummy()

sys.path.insert(0, str(_ROOT))

@suite("FilterService")
class TestFilterService:

    def _svc(self):
        from services.FilterService import FilterService
        return FilterService(dup_threshold=85)

    def test_import(self):
        from services.FilterService import FilterService
        _ = FilterService

    def test_preprocess_returns_required_keys(self):
        out = self._svc().preprocess(_QUERY)
        assert_keys(out, [
            "original", "cleaned", "intent", "intent_confidence",
            "keywords", "expanded_keywords",
        ], "preprocess")

    def test_preprocess_intent_is_valid(self):
        valid = {"research", "coding", "news", "comparison", "recommendation"}
        out   = self._svc().preprocess(_QUERY)
        assert_in(out["intent"], valid, "intent")

    def test_preprocess_confidence_range(self):
        out = self._svc().preprocess(_QUERY)
        assert_range(out["intent_confidence"], 0.0, 1.0, "intent_confidence")

    def test_preprocess_keywords_nonempty(self):
        out = self._svc().preprocess(_QUERY)
        if not out["keywords"]:
            fail("keywords list is empty")

    def test_postfilter_returns_all_results(self):

        out   = self._svc().postfilter(DUMMY_RESULTS, intent="research")
        n_in  = out.get("metadata", {}).get("total_input", -1)
        n_out = out.get("metadata", {}).get("total_output", -1)
        if n_in != len(DUMMY_RESULTS):
            fail(f"total_input={n_in}, expected {len(DUMMY_RESULTS)}")
        if n_out != len(DUMMY_RESULTS):
            fail(f"total_output={n_out}, expected {len(DUMMY_RESULTS)} (soft filter must not delete)")

    def test_postfilter_result_schema(self):
        out     = self._svc().postfilter(DUMMY_RESULTS, intent="research")
        results = out.get("results", [])
        if not results:
            fail("results list is empty")
        for r in results:
            assert_keys(r, [
                "title", "snippet", "url", "platform",
                "flags", "quality", "is_duplicate",
                "duplicate_score", "duplicate_of", "duplicate_group_id",
            ], "result schema")

    def test_postfilter_flags_low_quality(self):

        out           = self._svc().postfilter(DUMMY_RESULTS, intent="research")
        junk_snippets = {"Thanks!", "Following."}
        for r in out["results"]:
            if r["snippet"] in junk_snippets:
                if not r["flags"]:
                    fail(f"Expected flags on junk snippet: {r['snippet']!r}")

    def test_postfilter_quality_block_present(self):
        out = self._svc().postfilter(DUMMY_RESULTS, intent="research")
        for r in out["results"]:
            q = r.get("quality", {})
            assert_keys(q, ["has_title", "has_snippet", "snippet_length", "url_valid"], "quality")

    def test_postfilter_duplicate_detection(self):

        svc   = self._svc()
        duped = DUMMY_RESULTS[:3] + [DUMMY_RESULTS[0]] * 3
        out   = svc.postfilter(duped, intent="research")
        dupes = [r for r in out["results"] if r["is_duplicate"]]
        if len(dupes) < 2:
            fail(f"Expected ≥2 duplicates, got {len(dupes)}")

    def test_postfilter_duplicate_group_ids_consistent(self):

        svc  = self._svc()
        data = DUMMY_RESULTS[:2] + [DUMMY_RESULTS[0]]
        out  = svc.postfilter(data, intent="research")
        grp_ids = {
            r["duplicate_group_id"]
            for r in out["results"]
            if r["duplicate_group_id"] is not None
        }
        if grp_ids and len(grp_ids) > 1:
            fail(f"Multiple group IDs for one duplicate cluster: {grp_ids}")

    def test_postfilter_flags_summary_keys(self):
        out = self._svc().postfilter(DUMMY_RESULTS, intent="research")
        assert_keys(out.get("flags_summary", {}),
                    ["spam", "duplicates", "missing_fields"], "flags_summary")

    def test_postfilter_intent_variants(self):

        svc = self._svc()
        for intent in ("research", "coding", "news", "comparison", "recommendation"):
            svc.postfilter(DUMMY_RESULTS[:3], intent=intent)

    def test_postfilter_empty_input(self):
        out = self._svc().postfilter([], intent="research")
        if out.get("results") != []:
            fail("Empty input should return empty results list")

@suite("ScorerService")
class TestScorerService:

    _cached_svc = None

    def _svc(self):
        if TestScorerService._cached_svc is None:
            from services.ScorerService import ScorerService
            TestScorerService._cached_svc = ScorerService(model_name="all-MiniLM-L6-v2")
        return TestScorerService._cached_svc

    def test_import(self):
        from services.ScorerService import ScorerService
        _ = ScorerService

    def test_score_returns_list(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        assert_type(out, list, "score output")

    def test_score_preserves_all_results(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        if len(out) != len(DUMMY_RESULTS):
            fail(f"Expected {len(DUMMY_RESULTS)} results, got {len(out)}")

    def test_score_sorted_descending(self):
        out   = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        confs = [r["confidence"] for r in out]
        if confs != sorted(confs, reverse=True):
            fail(f"Results not sorted descending: {confs[:5]}")

    def test_score_confidence_range(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        for r in out:
            assert_range(r["confidence"], 0.0, 100.0, f"confidence for '{r['title'][:30]}'")

    def test_score_adds_reasons(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        for r in out:
            assert_type(r.get("reasons"), list, f"reasons for '{r['title'][:30]}'")

    def test_score_adds_breakdown(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        for r in out:
            bd = r.get("_score_breakdown", {})
            assert_keys(bd, ["semantic", "authority", "freshness", "engagement", "intent"],
                        "_score_breakdown")

    def test_score_breakdown_weights_sum_to_confidence(self):

        out   = self._svc().score(_QUERY, DUMMY_RESULTS[:1], intent="research")
        bd    = out[0]["_score_breakdown"]
        total = sum(v["weighted"] for v in bd.values())
        conf  = out[0]["confidence"]
        if not math.isclose(total, conf, rel_tol=0.05):
            fail(f"Breakdown total {total:.3f} ≠ confidence {conf:.3f}")

    def test_score_high_engagement_boosts_rank(self):

        out     = self._svc().score(_QUERY, DUMMY_RESULTS, intent="research")
        awesome = next((i for i, r in enumerate(out) if "Awesome" in r["title"]), None)
        random_ = next((i for i, r in enumerate(out) if "Random ML" in r["title"]), None)
        if awesome is not None and random_ is not None:
            if awesome > random_:
                fail(f"'Awesome ML' ranked #{awesome+1} but 'Random ML Scripts' ranked #{random_+1}")

    def test_score_intent_variants(self):
        svc = self._svc()
        for intent in ("research", "coding", "news", "comparison", "recommendation"):
            svc.score(_QUERY, DUMMY_RESULTS[:3], intent=intent)

    def test_score_empty_input(self):
        out = self._svc().score(_QUERY, [], intent="research")
        assert_eq(out, [], "empty input")

    def test_score_single_item(self):
        out = self._svc().score(_QUERY, DUMMY_RESULTS[:1], intent="research")
        if len(out) != 1:
            fail("Single-item input must return single-item output")

@suite("AgentService")
class TestAgentService:

    def _svc(self):
        from AgentService import ResearchAgent
        return ResearchAgent()

    def test_import(self):
        from AgentService import ResearchAgent
        _ = ResearchAgent

    def test_plan_returns_required_keys(self):
        out = self._svc().plan(_QUERY)
        assert_keys(out, [
            "question", "cleaned_question", "intent", "intent_confidence",
            "keywords", "query_variants", "source_weights", "strategy",
            "steps", "active_sources", "estimated_results", "created_at",
        ], "plan")

    def test_plan_intent_valid(self):
        valid = {"research", "coding", "news", "comparison", "recommendation"}
        out   = self._svc().plan(_QUERY)
        assert_in(out["intent"], valid, "intent")

    def test_plan_confidence_range(self):
        out = self._svc().plan(_QUERY)
        assert_range(out["intent_confidence"], 0.0, 1.0, "intent_confidence")

    def test_plan_source_weights_sum_to_1(self):
        out   = self._svc().plan(_QUERY)
        total = sum(out["source_weights"].values())
        if not math.isclose(total, 1.0, rel_tol=0.01):
            fail(f"source_weights sum to {total:.3f}, expected 1.0")

    def test_plan_source_weights_cover_all_sources(self):
        out      = self._svc().plan(_QUERY)
        expected = {"reddit", "github", "arxiv", "stackoverflow", "wikipedia", "news"}
        missing  = expected - set(out["source_weights"].keys())
        if missing:
            fail(f"Missing sources in source_weights: {missing}")

    def test_plan_steps_nonempty(self):
        out = self._svc().plan(_QUERY)
        if not out["steps"]:
            fail("steps list is empty")

    def test_plan_step_schema(self):
        out = self._svc().plan(_QUERY)
        for step in out["steps"]:
            assert_keys(step,
                        ["step_id", "phase", "objective", "sources", "rationale", "priority"],
                        "step")

    def test_plan_step_priority_valid(self):
        valid = {"high", "medium", "low"}
        out   = self._svc().plan(_QUERY)
        for step in out["steps"]:
            assert_in(step["priority"], valid, "step priority")

    def test_plan_query_variants_nonempty(self):
        out = self._svc().plan(_QUERY)
        if not out["query_variants"]:
            fail("query_variants is empty")

    def test_plan_active_sources_subset_of_all(self):
        all_src = {"reddit", "github", "arxiv", "stackoverflow", "wikipedia", "news"}
        out     = self._svc().plan(_QUERY)
        extra   = set(out["active_sources"]) - all_src
        if extra:
            fail(f"active_sources contains unknown sources: {extra}")

    def test_plan_strategy_valid(self):
        valid = {"academic_first", "solution_first", "recency_first",
                 "breadth_first", "community_first"}
        out   = self._svc().plan(_QUERY)
        assert_in(out["strategy"], valid, "strategy")

    def test_plan_intent_changes_with_query(self):
        svc     = self._svc()
        coding  = svc.plan("how do I fix this Python async bug")
        news_q  = svc.plan("latest AI news today 2025")
        intents = {coding["intent"], news_q["intent"]}
        if len(intents) == 1 and "research" in intents:
            fail("Intent detection appears stuck on 'research' for all queries")

    def test_describe_returns_string(self):
        svc  = self._svc()
        plan = svc.plan(_QUERY)
        out  = svc.describe(plan)
        assert_type(out, str, "describe")
        if len(out) < 50:
            fail(f"describe() returned suspiciously short string: {out!r}")

    def test_describe_contains_intent(self):
        svc  = self._svc()
        plan = svc.plan(_QUERY)
        out  = svc.describe(plan)
        if plan["intent"] not in out:
            fail(f"describe() output doesn't mention intent '{plan['intent']}'")

    def test_plan_short_query(self):
        out = self._svc().plan("AI")
        assert_keys(out, ["intent", "steps", "source_weights"], "short query plan")

    def test_plan_comparison_query(self):
        out = self._svc().plan("Python vs JavaScript for machine learning which is better?")
        if out["intent"] != "comparison":
            fail(f"Expected 'comparison' intent, got '{out['intent']}'")

@suite("DebateService")
class TestDebateService:

    def _svc(self):
        from DebateService import DebateService
        return DebateService()

    def _scored(self):
        from services.FilterService import FilterService
        filtered = FilterService().postfilter(DUMMY_RESULTS, intent="research")["results"]
        return TestScorerService._cached_svc.score(_QUERY, filtered, intent="research") \
               if TestScorerService._cached_svc else \
               __import__("services.ScorerService", fromlist=["ScorerService"]).ScorerService().score(
                   _QUERY, filtered, intent="research"
               )

    def test_import(self):
        from DebateService import DebateService
        _ = DebateService

    def test_analyze_returns_required_keys(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_keys(out, [
            "topic", "debate_type", "side_a", "side_b", "neutral",
            "agreement_points", "disagreement_points", "conclusion",
            "debate_intensity", "llm_prompt_context", "metadata",
        ], "analyze")

    def test_analyze_side_schema(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        for side_key in ("side_a", "side_b"):
            assert_keys(out[side_key],
                        ["label", "argument", "stance", "key_claims", "signal_words", "sources"],
                        side_key)

    def test_analyze_intensity_range(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_range(out["debate_intensity"], 0.0, 1.0, "debate_intensity")

    def test_analyze_debate_type_valid(self):
        valid = {"controversy", "comparison", "temporal", "methodological"}
        out   = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_in(out["debate_type"], valid, "debate_type")

    def test_analyze_sides_have_sources(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        for side_key in ("side_a", "side_b"):
            assert_type(out[side_key]["sources"], list, f"{side_key}.sources")

    def test_analyze_conclusion_nonempty(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        if not out.get("conclusion", "").strip():
            fail("conclusion is empty")

    def test_analyze_llm_prompt_context_nonempty(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        if not out.get("llm_prompt_context", "").strip():
            fail("llm_prompt_context is empty")

    def test_analyze_with_scored_results(self):

        out = self._svc().analyze(self._scored(), topic=_QUERY)
        assert_keys(out, ["side_a", "side_b", "conclusion"], "analyze with scored results")

    def test_analyze_empty_input(self):
        out = self._svc().analyze([], topic=_QUERY)
        assert_keys(out, ["topic", "side_a", "side_b"], "empty input")

    def test_analyze_single_item(self):
        out = self._svc().analyze(DUMMY_RESULTS[:1], topic=_QUERY)
        assert_keys(out, ["debate_intensity"], "single item")

    def test_analyze_rebalance_one_sided(self):

        pro_items = [
            {**r, "snippet": "Machine learning is absolutely the best way forward."}
            for r in DUMMY_RESULTS[:6]
        ]
        out = self._svc().analyze(pro_items, topic=_QUERY)
        assert_keys(out, ["side_a", "side_b", "debate_intensity"], "rebalance")

    def test_analyze_agreement_points_is_list(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_type(out["agreement_points"], list, "agreement_points")

    def test_analyze_disagreement_points_is_list(self):
        out = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_type(out["disagreement_points"], list, "disagreement_points")

    def test_analyze_metadata_present(self):
        out  = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        assert_keys(out.get("metadata", {}),
                    ["total_sources", "pro_count", "con_count", "neutral_count"], "metadata")

    def test_analyze_metadata_counts_sum(self):
        out  = self._svc().analyze(DUMMY_RESULTS, topic=_QUERY)
        meta = out["metadata"]
        total = meta["pro_count"] + meta["con_count"] + meta["neutral_count"]
        if total != meta["total_sources"]:
            fail(f"pro+con+neutral={total} ≠ total_sources={meta['total_sources']}")

@suite("GraphService")
class TestGraphService:

    def _svc(self):
        from GraphService import GraphService
        return GraphService(min_entity_freq=1, max_nodes=40)

    def _scored(self):
        from services.FilterService import FilterService
        filtered = FilterService().postfilter(DUMMY_RESULTS, intent="research")["results"]
        return TestScorerService._cached_svc.score(_QUERY, filtered, intent="research") \
               if TestScorerService._cached_svc else \
               __import__("services.ScorerService", fromlist=["ScorerService"]).ScorerService().score(
                   _QUERY, filtered, intent="research"
               )

    def test_import(self):
        from GraphService import GraphService
        _ = GraphService

    def test_build_graph_returns_required_keys(self):
        out = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        assert_keys(out, ["nodes", "edges", "metadata"], "build_graph")

    def test_build_graph_has_query_node(self):
        out   = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        types = [n["data"]["nodeType"] for n in out["nodes"]]
        assert_in("query", types, "nodeType=query")

    def test_build_graph_no_orphan_edges(self):
        out      = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        node_ids = {n["id"] for n in out["nodes"]}
        orphans  = [
            e for e in out["edges"]
            if e["source"] not in node_ids or e["target"] not in node_ids
        ]
        if orphans:
            fail(f"{len(orphans)} orphan edge(s): {orphans[:2]}")

    def test_build_graph_node_schema(self):
        out = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        for node in out["nodes"]:
            assert_keys(node, ["id", "type", "position", "data"], "node")
            assert_keys(node["position"], ["x", "y"], "node.position")
            assert_keys(node["data"],
                        ["label", "nodeType", "count", "platforms", "urls", "color"],
                        "node.data")

    def test_build_graph_edge_schema(self):
        out = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        for edge in out["edges"]:
            assert_keys(edge, ["id", "source", "target", "type", "label", "animated", "data"], "edge")
            assert_keys(edge["data"], ["relation", "weight", "strokeWidth"], "edge.data")

    def test_build_graph_no_self_loops(self):
        out   = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        loops = [e for e in out["edges"] if e["source"] == e["target"]]
        if loops:
            fail(f"{len(loops)} self-loop edge(s) found")

    def test_build_graph_no_duplicate_edges(self):
        out  = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        seen: set[frozenset] = set()
        for e in out["edges"]:
            pair = frozenset({e["source"], e["target"]})
            if pair in seen:
                fail(f"Duplicate edge: {e['source']} ↔ {e['target']}")
            seen.add(pair)

    def test_build_graph_no_stopword_entities(self):

        out       = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        stopwords = {
            "What", "It", "Is", "Are", "This", "That", "The", "A", "An",
            "I", "We", "You", "He", "She", "They", "Can", "Do", "How",
        }
        for node in out["nodes"]:
            label = node["data"]["label"]
            if label in stopwords:
                fail(f"Stopword entity in graph: {label!r}")

    def test_build_graph_metadata_counts(self):
        out  = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        meta = out["metadata"]
        assert_keys(meta, ["total_nodes", "total_edges", "spacy_active"], "metadata")
        if meta["total_nodes"] != len(out["nodes"]):
            fail(f"metadata.total_nodes={meta['total_nodes']} ≠ len(nodes)={len(out['nodes'])}")
        if meta["total_edges"] != len(out["edges"]):
            fail(f"metadata.total_edges={meta['total_edges']} ≠ len(edges)={len(out['edges'])}")

    def test_build_graph_node_types_valid(self):
        from GraphService import GraphService
        out   = GraphService(min_entity_freq=1, max_nodes=40).build_graph(DUMMY_RESULTS, query=_QUERY)
        valid = {
            "queryNode", "topicNode", "techNode", "orgNode",
            "personNode", "platformNode", "conceptNode", "locationNode",
        }
        for node in out["nodes"]:
            if node["type"] not in valid:
                fail(f"Unknown React Flow node type: {node['type']!r}")

    def test_build_graph_platform_nodes_present(self):

        out       = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        plat_lbls = {
            n["data"]["label"].lower()
            for n in out["nodes"]
            if n["data"]["nodeType"] == "platform"
        }
        missing = {"reddit", "github", "arxiv"} - plat_lbls
        if missing:
            fail(f"Missing platform nodes: {missing}")

    def test_build_graph_with_scored_input(self):

        out = self._svc().build_graph(self._scored(), query=_QUERY)
        assert_keys(out, ["nodes", "edges", "metadata"], "scored input")

    def test_build_graph_empty_input(self):
        out = self._svc().build_graph([], query=_QUERY)
        if out.get("nodes") is None or out.get("edges") is None:
            fail("Empty input should return nodes=[] and edges=[], not None")

    def test_build_graph_stroke_width_capped(self):

        out = self._svc().build_graph(DUMMY_RESULTS, query=_QUERY)
        for edge in out["edges"]:
            assert_range(edge["data"]["strokeWidth"], 1, 6, "strokeWidth")

    def test_build_graph_node_count_respects_max(self):

        from GraphService import GraphService
        svc  = GraphService(min_entity_freq=1, max_nodes=10)
        out  = svc.build_graph(DUMMY_RESULTS * 5, query=_QUERY)
        real = [n for n in out["nodes"] if n["data"]["nodeType"] not in ("query", "platform")]
        if len(real) > 10:
            fail(f"max_nodes=10 but got {len(real)} non-platform/query nodes")

@suite("Full Pipeline")
class TestFullPipeline:

    def _run(self, data=None, query=None):
        from services.FilterService import FilterService
        from services.ScorerService import ScorerService
        from DebateService           import DebateService
        from GraphService            import GraphService

        data  = data  or DUMMY_RESULTS
        query = query or _QUERY

        filtered = FilterService().postfilter(data, intent="research")["results"]
        scored   = ScorerService().score(query, filtered, intent="research")
        debate   = DebateService().analyze(scored, topic=query)
        graph    = GraphService(min_entity_freq=1, max_nodes=30).build_graph(scored, query=query)
        return filtered, scored, debate, graph

    def test_pipeline_runs_without_exception(self):
        self._run()

    def test_pipeline_soft_filter_preserves_count(self):
        filtered, *_ = self._run()
        if len(filtered) != len(DUMMY_RESULTS):
            fail(f"Filter dropped items: {len(filtered)} ≠ {len(DUMMY_RESULTS)}")

    def test_pipeline_scorer_output_is_sorted(self):
        _, scored, *_ = self._run()
        confs = [r["confidence"] for r in scored]
        if confs != sorted(confs, reverse=True):
            fail("Scorer output not sorted descending")

    def test_pipeline_schema_passthrough(self):

        _, scored, *_ = self._run()
        base_keys = {"title", "snippet", "url", "platform", "date", "author", "engagement"}
        for r in scored:
            missing = base_keys - set(r.keys())
            if missing:
                fail(f"ScorerService dropped keys: {missing}")

    def test_pipeline_filter_adds_annotation_keys(self):
        filtered, *_ = self._run()
        for r in filtered:
            assert_keys(r, ["flags", "quality", "is_duplicate", "duplicate_group_id"],
                        "filter annotation")

    def test_pipeline_scorer_adds_score_keys(self):
        _, scored, *_ = self._run()
        for r in scored:
            assert_keys(r, ["confidence", "reasons", "_score_breakdown"], "score annotation")

    def test_pipeline_debate_has_both_sides(self):
        *_, debate, _graph = self._run()
        assert_keys(debate, ["side_a", "side_b", "conclusion", "debate_intensity"], "debate")

    def test_pipeline_graph_has_no_orphans(self):
        *_, graph = self._run()
        node_ids = {n["id"] for n in graph["nodes"]}
        orphans  = [e for e in graph["edges"]
                    if e["source"] not in node_ids or e["target"] not in node_ids]
        if orphans:
            fail(f"{len(orphans)} orphan edge(s) in pipeline graph")

    def test_pipeline_confidence_higher_for_relevant_results(self):

        _, scored, *_ = self._run()
        survey_conf = next((r["confidence"] for r in scored if "Survey" in r["title"]), None)
        thanks_conf = next((r["confidence"] for r in scored if r["snippet"] == "Thanks!"), None)
        if survey_conf is not None and thanks_conf is not None:
            if survey_conf <= thanks_conf:
                fail(f"Survey ({survey_conf:.1f}) should outscore 'Thanks!' ({thanks_conf:.1f})")

    def test_pipeline_agent_plan_then_pipeline(self):

        from AgentService           import ResearchAgent
        from services.FilterService import FilterService
        from services.ScorerService import ScorerService

        plan   = ResearchAgent().plan(_QUERY)
        intent = plan["intent"]

        filtered = FilterService().postfilter(DUMMY_RESULTS, intent=intent)["results"]
        scored   = ScorerService().score(_QUERY, filtered, intent=intent)
        if not scored:
            fail("Pipeline with agent-derived intent returned no results")

def _run_suite(suite_name: str, cls: type, tests: list[tuple[str, str]]) -> tuple[int, int]:
    passed = failed = 0
    print(f"\n{BOLD(suite_name)}")
    print("─" * 60)

    instance = cls()

    for label, method_name in tests:
        t0 = time.perf_counter()
        try:
            getattr(instance, method_name)()
            elapsed = int((time.perf_counter() - t0) * 1000)
            passed += 1
            if _VERBOSE:
                print(f"  {GREEN('✓')} {label}  {DIM(f'{elapsed}ms')}")
        except Exception as exc:
            elapsed = int((time.perf_counter() - t0) * 1000)
            failed += 1
            print(f"  {RED('✗')} {label}  {DIM(f'{elapsed}ms')}")
            msg = str(exc) if isinstance(exc, AssertionError) else f"{type(exc).__name__}: {exc}"
            print(f"      {RED(msg)}")
            if _VERBOSE and not isinstance(exc, AssertionError):
                for line in traceback.format_exc().splitlines()[-8:]:
                    print(f"      {DIM(line)}")

    if not _VERBOSE:
        status = (
            GREEN(f"✓ {passed} passed")
            if not failed
            else f"{GREEN(f'{passed} passed')}  {RED(f'{failed} failed')}"
        )
        print(f"  {status}")

    return passed, failed

def main() -> int:
    requested = [a for a in sys.argv[1:] if not a.startswith("-")]
    suites_to_run = (
        {k: v for k, v in _SUITES.items()
         if any(r.lower() in k.lower() for r in requested)}
        if requested else _SUITES
    )

    if not suites_to_run:
        print(f"{RED('No matching suites:')} {requested}")
        print(f"Available: {list(_SUITES.keys())}")
        return 1

    print(f"\n{BOLD('Intelligence Layer Test Suite')}")
    print(f"Query : {DIM(_QUERY)}")
    print(f"Data  : {DIM(str(_DUMMY_PATH))}  ({len(DUMMY_RESULTS)} records)")
    print(f"Suites: {', '.join(suites_to_run.keys())}")

    total_pass = total_fail = 0
    t_start    = time.perf_counter()

    for name, (cls, tests) in suites_to_run.items():
        p, f = _run_suite(name, cls, tests)
        total_pass += p
        total_fail += f

    elapsed = time.perf_counter() - t_start
    print(f"\n{'─'*60}")
    print(f"  {BOLD('Total:')}  {GREEN(f'{total_pass} passed')}  ", end="")
    if total_fail:
        print(f"{RED(f'{total_fail} failed')}  ", end="")
    print(f"{DIM(f'in {elapsed:.1f}s')}")

    if total_fail == 0:
        print(f"\n  {GREEN('All tests passed ✓')}")
    else:
        print(f"\n  {RED(f'{total_fail} test(s) failed ✗')}")

    return 0 if total_fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
