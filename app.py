

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

load_dotenv()

from services.AnalyzerService import AnalyzerService
from services.FilterService   import FilterService
from services.ScorerService   import ScorerService
from AgentService              import ResearchAgent
from DebateService             import DebateService
from GraphService              import GraphService

try:
    from services.LLMService import LLMService
    _llm_class_available = True
except ImportError:
    _llm_class_available = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("app")

_services: dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: Starlette):
    logger.info("Initializing services…")

    _services["analyzer"] = AnalyzerService(
        timeout=12.0,
        news_api_key=os.environ.get("NEWS_API_KEY", ""),
    )
    _services["filter"]   = FilterService(dup_threshold=85)
    _services["agent"]    = ResearchAgent()
    _services["debate"]   = DebateService()
    _services["graph"]    = GraphService(min_entity_freq=1, max_nodes=40)

    try:
        _services["scorer"] = ScorerService(model_name="all-MiniLM-L6-v2")
        logger.info("ScorerService ready  (all-MiniLM-L6-v2)")
    except Exception as exc:
        logger.warning("ScorerService unavailable: %s", exc)
        _services["scorer"] = None

    llm_key = os.environ.get("GROQ_API_KEY", "")
    if _llm_class_available and llm_key:
        try:
            _services["llm"] = LLMService(api_key=llm_key)
            logger.info("LLMService ready  (groq / llama-3.3-70b-versatile)")
        except Exception as exc:
            logger.warning("LLMService unavailable: %s", exc)
            _services["llm"] = None
    else:
        if not llm_key:
            logger.warning("GROQ_API_KEY not set — LLM synthesis disabled.")
        _services["llm"] = None

    logger.info("All services initialized.")
    yield
    _services.clear()
    logger.info("Shutdown complete.")

_ALL_SOURCES = ["reddit", "github", "arxiv", "stackoverflow", "wikipedia", "news"]

def _svc(name: str) -> Any:
    return _services.get(name)

def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)

def _bad(message: str, status: int = 422) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status)

def _parse_max_results(body: dict, default: int = 50, cap: int = 200) -> int | JSONResponse:
    raw = body.get("max_results", default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _bad(f"'max_results' must be an integer, got: {raw!r}")
    return min(max(value, 1), cap)

async def _parse_body(request: Request) -> dict | JSONResponse:
    try:
        return await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body."}, status_code=400)

async def _run_pipeline(
    query:          str,
    sources:        list[str] | None,
    max_results:    int,
    include_debate: bool,
    include_graph:  bool,
    include_llm:    bool,
    pre_fetched:    list[dict] | None = None,
) -> dict[str, Any]:
    t_total = time.perf_counter()
    timing:  dict[str, int] = {}
    errors:  dict[str, Any] = {}

    t0   = time.perf_counter()
    plan = _svc("agent").plan(query)
    timing["plan_ms"] = _ms(t0)

    intent           = plan.get("intent", "research")
    resolved_sources = sources or list(plan.get("source_weights", {}).keys()) or _ALL_SOURCES

    if pre_fetched is not None:
        raw_results      = pre_fetched
        resolved_sources = list({r.get("platform", "unknown") for r in raw_results})
        timing["fetch_ms"] = 0
    else:
        t0 = time.perf_counter()
        try:
            raw_output   = await _svc("analyzer").fetch_all(query, sources=resolved_sources)
            raw_results  = raw_output.get("results", [])
            fetch_errors = raw_output.get("errors", {})
        except Exception as exc:
            logger.error("AnalyzerService failed: %s", exc)
            return {"error": f"Source fetch failed: {exc}", "query": query}
        timing["fetch_ms"] = _ms(t0)
        if fetch_errors:
            errors["fetch"] = fetch_errors

    if not raw_results:
        return {
            "query": query, "plan": plan,
            "ranked_sources": [], "filter_summary": {},
            "debate": None, "graph": None, "llm_response": None,
            "meta": {
                "intent": intent, "sources_used": resolved_sources,
                "total_raw": 0, "total_ranked": 0,
                "timing_ms": timing, "errors": errors,
            },
        }

    t0 = time.perf_counter()
    try:
        filter_out     = _svc("filter").postfilter(raw_results, intent=intent)
        clean_results  = filter_out.get("results", raw_results)
        filter_summary = {
            "total_input":   filter_out.get("metadata", {}).get("total_input",  len(raw_results)),
            "total_output":  filter_out.get("metadata", {}).get("total_output", len(clean_results)),
            "flags_summary": filter_out.get("flags_summary", {}),
        }
    except Exception as exc:
        logger.warning("FilterService error: %s", exc)
        clean_results  = raw_results
        filter_summary = {}
        errors["filter"] = str(exc)
    timing["filter_ms"] = _ms(t0)

    t0     = time.perf_counter()
    scorer = _svc("scorer")
    if scorer and clean_results:
        try:
            ranked = scorer.score(query, clean_results, intent=intent)
        except Exception as exc:
            logger.warning("ScorerService error: %s", exc)
            ranked = clean_results
            errors["scorer"] = str(exc)
    else:
        ranked = clean_results

    _STOP = {
        "use", "the", "and", "for", "are", "but", "not", "you", "all", "any",
        "can", "had", "has", "its", "out", "was", "who", "did", "how", "let",
        "may", "say", "she", "too", "why", "does", "per", "via", "yet",
        "should", "would", "could", "will", "what", "when", "where", "which",
        "this", "that", "with", "from", "into", "have", "been", "than", "then",
        "them", "they", "there", "their", "about", "some", "also", "just",
        "like", "over", "such", "much", "even", "well", "only", "most", "both",
        "each", "very", "need", "make", "time", "know", "take", "good", "best",
        "want", "look", "come", "give", "work", "long", "down", "back", "going",
        "being", "using", "getting", "having", "making", "doing",
    }
    main_keywords = {
        w.lower() for w in query.split()
        if len(w) > 2 and w.lower() not in _STOP
    }
    def _is_relevant(r: dict) -> bool:
        if r.get("confidence", 0) >= 50:
            return True
        if not main_keywords:
            return True
        title = (r.get("title") or "").lower()
        return any(kw in title for kw in main_keywords)

    ranked = [r for r in ranked if _is_relevant(r)]
    ranked_results = ranked[:max_results]
    timing["score_ms"] = _ms(t0)

    debate_out: dict | None = None
    debate_svc = _svc("debate")
    if include_debate and debate_svc and ranked_results:
        t0 = time.perf_counter()
        try:
            debate_out = debate_svc.analyze(ranked_results, topic=query)
        except Exception as exc:
            logger.warning("DebateService error: %s", exc)
            errors["debate"] = str(exc)
        timing["debate_ms"] = _ms(t0)
    elif include_debate and not debate_svc:
        errors["debate"] = "DebateService unavailable."

    graph_out: dict | None = None
    graph_svc = _svc("graph")
    if include_graph and graph_svc and ranked_results:
        t0 = time.perf_counter()
        try:
            graph_out = graph_svc.build_graph(ranked_results, query=query)
        except Exception as exc:
            logger.warning("GraphService error: %s", exc)
            errors["graph"] = str(exc)
        timing["graph_ms"] = _ms(t0)
    elif include_graph and not graph_svc:
        errors["graph"] = "GraphService unavailable."

    llm_out: dict | None = None
    llm_svc = _svc("llm")
    if include_llm and llm_svc and ranked_results:
        t0 = time.perf_counter()
        try:
            llm_out = await llm_svc.generate_research_response(
                query          = query,
                ranked_sources = ranked_results,
                debate_results = debate_out,
                research_graph = graph_out,
                intent         = intent,
            )
        except Exception as exc:
            logger.warning("LLMService error: %s", exc)
            errors["llm"] = str(exc)
        timing["llm_ms"] = _ms(t0)
    elif include_llm and not llm_svc:
        errors["llm"] = "LLMService unavailable — set GEMINI_API_KEY to enable."

    timing["total_ms"] = _ms(t_total)

    return {
        "query":          query,
        "plan":           plan,
        "ranked_sources": ranked_results,
        "filter_summary": filter_summary,
        "debate":         debate_out,
        "graph":          graph_out,
        "llm_response":   llm_out,
        "meta": {
            "intent":       intent,
            "sources_used": resolved_sources,
            "total_raw":    len(raw_results),
            "total_ranked": len(ranked_results),
            "timing_ms":    timing,
            "errors":       errors,
        },
    }

async def health(request: Request) -> JSONResponse:
    llm = _svc("llm")
    return JSONResponse({
        "status": "ok",
        "services": {
            name: _svc(name) is not None
            for name in ("analyzer", "filter", "scorer", "agent", "debate", "graph", "llm")
        },
        "llm_model": getattr(llm, "_model_name", None),
    })

async def research(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    sources     = body.get("sources")
    max_results = _parse_max_results(body)
    if isinstance(max_results, JSONResponse):
        return max_results

    result = await _run_pipeline(
        query          = query,
        sources        = sources,
        max_results    = max_results,
        include_debate = bool(body.get("include_debate", True)),
        include_graph  = bool(body.get("include_graph",  True)),
        include_llm    = bool(body.get("include_llm",    True)),
    )
    return JSONResponse(result)

async def research_plan(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    agent = _svc("agent")
    plan  = agent.plan(query)
    return JSONResponse({
        "query":       query,
        "plan":        plan,
        "description": agent.describe(plan),
    })

async def research_sources(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    max_results = _parse_max_results(body)
    if isinstance(max_results, JSONResponse):
        return max_results

    result = await _run_pipeline(
        query          = query,
        sources        = body.get("sources"),
        max_results    = max_results,
        include_debate = False,
        include_graph  = False,
        include_llm    = False,
    )
    return JSONResponse(result)

async def research_debate(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    max_results = _parse_max_results(body)
    if isinstance(max_results, JSONResponse):
        return max_results

    result = await _run_pipeline(
        query          = query,
        sources        = body.get("sources"),
        max_results    = max_results,
        include_debate = True,
        include_graph  = False,
        include_llm    = False,
    )
    return JSONResponse(result)

async def research_graph(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    max_results = _parse_max_results(body)
    if isinstance(max_results, JSONResponse):
        return max_results

    result = await _run_pipeline(
        query          = query,
        sources        = body.get("sources"),
        max_results    = max_results,
        include_debate = False,
        include_graph  = True,
        include_llm    = False,
    )
    return JSONResponse(result)

async def analyze(request: Request) -> JSONResponse:

    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    query = str(body.get("query", "")).strip()
    if len(query) < 2:
        return _bad("'query' must be at least 2 characters.")

    results = body.get("results")
    if not isinstance(results, list) or not results:
        return _bad("'results' must be a non-empty array of source objects.")

    max_results = _parse_max_results(body)
    if isinstance(max_results, JSONResponse):
        return max_results

    result = await _run_pipeline(
        query          = query,
        sources        = None,
        max_results    = max_results,
        include_debate = bool(body.get("include_debate", True)),
        include_graph  = bool(body.get("include_graph",  True)),
        include_llm    = bool(body.get("include_llm",    True)),
        pre_fetched    = results,
    )
    return JSONResponse(result)

async def webhook(request: Request) -> JSONResponse:

    try:
        data = await request.json()
    except Exception:
        data = {}
    return JSONResponse({"message": "Webhook received successfully!", "received": data})

async def openapi_schema(request: Request) -> JSONResponse:
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "AI Research Engine",
            "version": "1.0.0",
            "description": "7-stage intelligence pipeline: plan → fetch → filter → score → debate → graph → LLM synthesis",
        },
        "servers": [{"url": "http://localhost:8000"}],
        "paths": {
            "/": {
                "get": {
                    "summary": "Health check",
                    "description": "Returns status and which services are active.",
                    "operationId": "health",
                    "tags": ["System"],
                    "responses": {"200": {"description": "Service status"}},
                }
            },
            "/research": {
                "post": {
                    "summary": "Full 7-stage pipeline",
                    "description": "Runs the complete pipeline: plan → fetch → filter → score → debate → graph → LLM synthesis.",
                    "operationId": "research",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ResearchRequest"}}},
                    },
                    "responses": {"200": {"description": "Full pipeline result"}},
                }
            },
            "/research/plan": {
                "post": {
                    "summary": "Research plan only",
                    "description": "Returns the intent-aware research plan without fetching any sources.",
                    "operationId": "research_plan",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/QueryRequest"}}},
                    },
                    "responses": {"200": {"description": "Research plan"}},
                }
            },
            "/research/sources": {
                "post": {
                    "summary": "Fetch + filter + score only",
                    "description": "Runs stages 1-4 (no debate, graph, or LLM).",
                    "operationId": "research_sources",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SourcesRequest"}}},
                    },
                    "responses": {"200": {"description": "Ranked sources"}},
                }
            },
            "/research/debate": {
                "post": {
                    "summary": "Fetch + debate analysis",
                    "description": "Runs stages 1-5: fetches sources and runs pro/con conflict detection.",
                    "operationId": "research_debate",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SourcesRequest"}}},
                    },
                    "responses": {"200": {"description": "Debate analysis"}},
                }
            },
            "/research/graph": {
                "post": {
                    "summary": "Fetch + knowledge graph",
                    "description": "Runs stages 1-4 + graph extraction. Returns React Flow-compatible nodes and edges.",
                    "operationId": "research_graph",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SourcesRequest"}}},
                    },
                    "responses": {"200": {"description": "Knowledge graph (nodes + edges)"}},
                }
            },
            "/analyze": {
                "post": {
                    "summary": "Analyze pre-fetched results",
                    "description": "Skip the fetch stage — send your own results array and get back filter → score → debate → graph → LLM synthesis. Use this when your backend already fetched the sources.",
                    "operationId": "analyze",
                    "tags": ["Research"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AnalyzeRequest"}}},
                    },
                    "responses": {"200": {"description": "Full intelligence pipeline result"}},
                }
            },
            "/hook": {
                "post": {
                    "summary": "Inbound webhook",
                    "description": "Generic webhook receiver.",
                    "operationId": "webhook",
                    "tags": ["System"],
                    "requestBody": {
                        "required": False,
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "responses": {"200": {"description": "Acknowledgement"}},
                }
            },
        },
        "components": {
            "schemas": {
                "QueryRequest": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "example": "transformer neural networks", "minLength": 2},
                    },
                },
                "SourcesRequest": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "example": "transformer neural networks", "minLength": 2},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["reddit", "github", "arxiv", "stackoverflow", "wikipedia", "news"]},
                            "example": ["arxiv", "github", "wikipedia"],
                        },
                        "max_results": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200, "example": 15},
                    },
                },
                "SourceItem": {
                    "type": "object",
                    "required": ["title", "url", "platform"],
                    "properties": {
                        "title":      {"type": "string", "example": "Attention Is All You Need"},
                        "snippet":    {"type": "string", "example": "We propose the Transformer architecture..."},
                        "url":        {"type": "string", "example": "https://arxiv.org/abs/1706.03762"},
                        "platform":   {"type": "string", "example": "Arxiv", "enum": ["Arxiv", "GitHub", "Wikipedia", "StackOverflow", "News", "Reddit"]},
                        "date":       {"type": "string", "example": "2024-01-15T00:00:00Z"},
                        "author":     {"type": "string", "example": "Vaswani et al."},
                        "engagement": {"type": "integer", "example": 500},
                    },
                },
                "AnalyzeRequest": {
                    "type": "object",
                    "required": ["query", "results"],
                    "properties": {
                        "query": {"type": "string", "example": "transformer neural networks", "minLength": 2},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SourceItem"},
                            "minItems": 1,
                        },
                        "max_results":    {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
                        "include_debate": {"type": "boolean", "default": True},
                        "include_graph":  {"type": "boolean", "default": True},
                        "include_llm":    {"type": "boolean", "default": True},
                    },
                },
                "ResearchRequest": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "example": "large language models vs traditional ML", "minLength": 2},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["reddit", "github", "arxiv", "stackoverflow", "wikipedia", "news"]},
                        },
                        "max_results": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200, "example": 15},
                        "include_debate": {"type": "boolean", "default": True},
                        "include_graph":  {"type": "boolean", "default": True},
                        "include_llm":    {"type": "boolean", "default": True},
                    },
                },
            }
        },
    }
    return JSONResponse(schema)

async def swagger_ui(request: Request) -> HTMLResponse:
    html = """<!DOCTYPE html>
<html>
<head>
  <title>AI Research Engine — API Docs</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
    deepLinking: true,
    defaultModelsExpandDepth: 1,
    defaultModelExpandDepth: 1,
  })
</script>
</body>
</html>"""
    return HTMLResponse(html)

async def not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Not found."}, status_code=404)

async def server_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse({"detail": "Internal server error.", "error": str(exc)}, status_code=500)

app = Starlette(
    debug=False,
    routes=[
        Route("/",                 health,           methods=["GET"]),
        Route("/docs",             swagger_ui,       methods=["GET"]),
        Route("/openapi.json",     openapi_schema,   methods=["GET"]),
        Route("/research",         research,         methods=["POST"]),
        Route("/research/plan",    research_plan,    methods=["POST"]),
        Route("/research/sources", research_sources, methods=["POST"]),
        Route("/research/debate",  research_debate,  methods=["POST"]),
        Route("/research/graph",   research_graph,   methods=["POST"]),
        Route("/analyze",          analyze,          methods=["POST"]),
        Route("/hook",             webhook,          methods=["POST"]),
    ],
    exception_handlers={404: not_found, 500: server_error},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
