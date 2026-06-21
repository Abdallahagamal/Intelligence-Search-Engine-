

from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter, defaultdict
from typing import Any

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    _SPACY_OK = True
except Exception:
    _nlp       = None
    _SPACY_OK  = False

_LABEL_TO_TYPE: dict[str, str] = {
    "PERSON":     "person",
    "ORG":        "organization",
    "PRODUCT":    "technology",
    "GPE":        "location",
    "LOC":        "location",
    "EVENT":      "event",
    "WORK_OF_ART":"concept",
    "NORP":       "group",
    "LAW":        "regulation",
    "LANGUAGE":   "language",
    "FAC":        "facility",
}

_ORG_SUFFIXES: tuple[str, ...] = (
    " ai", " inc", " inc.", " corp", " corp.", " ltd", " ltd.",
    " llc", " llp", " labs", " lab", " technologies", " tech",
    " systems", " solutions", " ventures", " capital", " group",
    " foundation", " institute", " university", " college",
    " research", " robotics", " analytics",
)

_TECH_TOKENS: frozenset[str] = frozenset({
    "gpt", "bert", "llm", "api", "sdk", "gpu", "cpu", "model",
    "framework", "library", "platform", "algorithm", "network",
    "transformer", "diffusion", "dataset", "benchmark",
})

def _override_entity_type(label: str, spacy_type: str) -> str:

    lower = label.lower()
    tokens = set(re.findall(r"[a-z]+", lower))

    if any(lower.endswith(sfx) for sfx in _ORG_SUFFIXES):
        return "organization"

    if re.search(r"\bai\b", lower) or lower.endswith("ai"):
        return "organization"

    if tokens & _TECH_TOKENS:
        return "technology"

    return spacy_type

_SKIP_LABELS: frozenset[str] = frozenset({
    "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY",
    "ORDINAL", "CARDINAL",
})

_TYPE_COLOR: dict[str, str] = {
    "query":        "#6366f1",
    "topic":        "#06b6d4",
    "organization": "#ef4444",
    "person":       "#f59e0b",
    "technology":   "#10b981",
    "concept":      "#3b82f6",
    "location":     "#8b5cf6",
    "group":        "#ec4899",
    "event":        "#f97316",
    "regulation":   "#64748b",
    "language":     "#84cc16",
    "platform":     "#334155",
    "facility":     "#a3a3a3",
    "unknown":      "#9ca3af",
}

_EDGE_TYPES: dict[str, str] = {
    "related_to":     "smoothstep",
    "co_occurs_with": "default",
    "found_on":       "straight",
    "discusses":      "step",
    "mentions":       "smoothstep",
}

_MIN_LABEL_LEN = 3

_RICH_DEPS = frozenset({
    "nsubj", "nsubjpass", "dobj", "pobj", "attr", "appos",
})

_GRAPH_STOPWORDS: frozenset[str] = frozenset({

    "What", "Which", "Who", "Whom", "Whose", "When", "Where", "Why", "How",

    "This", "That", "These", "Those", "It", "Its",
    "I", "Me", "My", "Mine", "We", "Us", "Our", "Ours",
    "He", "Him", "His", "She", "Her", "Hers",
    "They", "Them", "Their", "Theirs", "You", "Your", "Yours",

    "The", "A", "An", "Some", "Any", "All", "Each", "Every", "Both",
    "Few", "More", "Most", "Other", "Such", "No", "Not", "None",

    "Is", "Are", "Was", "Were", "Be", "Been", "Being",
    "Has", "Have", "Had", "Do", "Does", "Did",
    "Can", "Could", "Will", "Would", "Should", "May", "Might", "Must", "Shall",
    "Get", "Gets", "Got", "Make", "Makes", "Made", "Use", "Uses", "Used",
    "See", "Sees", "Show", "Shows", "Find", "Finds", "Found",

    "In", "On", "At", "To", "For", "Of", "By", "With", "From", "As",
    "And", "Or", "But", "If", "So", "Yet", "Nor", "Also", "However",

    "New", "Old", "Good", "Bad", "Big", "Large", "Small",
    "High", "Low", "First", "Last", "Best", "Worst",
    "Many", "Much", "Same", "Different", "Similar", "Various",

    "Way", "Ways", "Time", "Day", "Year", "Work", "Part",
    "Case", "Point", "Number", "Results", "Result",
    "Data", "Information", "Content", "Paper", "Papers",
    "Section", "Figure", "Table", "Example", "Based",
})

_BIGRAM_STOPWORDS: frozenset[str] = frozenset(w.lower() for w in _GRAPH_STOPWORDS) | frozenset({
    "the", "a", "an", "of", "in", "on", "for", "and", "or", "but",
    "is", "to", "with", "how", "what", "why", "when", "its", "as",
    "by", "from", "that", "this", "be", "are", "was", "were", "not",
    "at", "if", "so", "we", "it", "do", "has", "have", "had", "can",
})

_FALLBACK_PATTERNS: list[tuple[re.Pattern, str]] = [

    (re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})+)\b"), "concept"),

    (re.compile(r"\b(AI|ML|NLP|LLM|API|GPU|CPU|RAG|GAN|BERT|GPT|CNN|RNN|SVM|RLHF|LoRA|QLoRA)\b"), "technology"),

    (re.compile(r"\b([A-Z][a-zA-Z]{2,}[-\s]?\d+(?:\.\d+)?)\b"), "technology"),
]

class GraphService:

    def __init__(
        self,
        min_entity_freq: int   = 1,
        max_nodes:        int   = 50,
        model:            str   = "en_core_web_sm",
    ) -> None:

        self.min_entity_freq = min_entity_freq
        self.max_nodes       = max_nodes

        if _SPACY_OK:
            self._nlp = _nlp
        else:
            self._nlp = None

    def build_graph(
        self,
        results: list[dict[str, Any]],
        query:   str = "",
    ) -> dict[str, Any]:

        t0 = time.perf_counter()

        if not results:
            return self._empty_graph(query, t0)

        entity_records  = self._extract_entities(results)
        topic_records   = self._extract_topics(results)

        entity_map  = self._deduplicate(entity_records)
        topic_map   = self._deduplicate(topic_records, prefix="topic")
        combined    = self._merge_maps(entity_map, topic_map)

        top_entities = sorted(
            combined.values(),
            key=lambda x: x["count"],
            reverse=True,
        )[: self.max_nodes]

        nodes, node_lookup = self._build_nodes(query, top_entities, results)

        edges = self._build_edges(
            query, top_entities, entity_records, results, node_lookup
        )

        self._apply_layout(nodes, edges)

        elapsed = round(time.perf_counter() - t0, 3)

        node_type_counts: Counter[str] = Counter(
            n["data"]["nodeType"] for n in nodes
        )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_results":    len(results),
                "total_nodes":      len(nodes),
                "total_edges":      len(edges),
                "node_types":       dict(node_type_counts),
                "platforms":        sorted({r.get("platform", "") for r in results if r.get("platform")}),
                "spacy_active":     _SPACY_OK,
                "extraction_ms":    int(elapsed * 1000),
            },
        }

    def _extract_entities(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:

        if self._nlp:
            return self._extract_with_spacy(results)
        return self._extract_with_regex(results)

    def _extract_with_spacy(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        texts = [
            f"{r.get('title', '')}. {r.get('snippet', '')}"
            for r in results
        ]
        records: list[dict[str, Any]] = []
        for result, doc in zip(results, self._nlp.pipe(texts, batch_size=32)):
            title_lower = (result.get("title") or "").lower()
            for ent in doc.ents:
                if ent.label_ in _SKIP_LABELS:
                    continue
                label = ent.text.strip()
                if len(label) < _MIN_LABEL_LEN:
                    continue
                entity_type = _override_entity_type(
                    label, _LABEL_TO_TYPE.get(ent.label_, "concept")
                )
                records.append({
                    "text":        label,
                    "entity_type": entity_type,
                    "result_url":  result.get("url", ""),
                    "platform":    result.get("platform", ""),
                    "in_title":    label.lower() in title_lower,
                })
        return records

    def _extract_with_regex(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for result in results:
            text = f"{result.get('title', '')} {result.get('snippet', '')}"
            title_lower = (result.get("title") or "").lower()
            seen_in_result: set[str] = set()
            for pattern, entity_type in _FALLBACK_PATTERNS:
                for match in pattern.finditer(text):
                    label = match.group(0).strip()
                    norm  = label.lower()
                    if len(label) < _MIN_LABEL_LEN:
                        continue
                    if label in _GRAPH_STOPWORDS or norm in seen_in_result:
                        continue

                    first_word = label.split()[0]
                    if first_word in _GRAPH_STOPWORDS:
                        continue
                    seen_in_result.add(norm)
                    records.append({
                        "text":        label,
                        "entity_type": entity_type,
                        "result_url":  result.get("url", ""),
                        "platform":    result.get("platform", ""),
                        "in_title":    label.lower() in title_lower,
                    })
        return records

    def _extract_topics(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:

        if self._nlp:
            return self._topics_with_spacy(results)
        return self._topics_from_titles(results)

    def _topics_with_spacy(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        title_texts = [r.get("title", "") for r in results]
        records: list[dict[str, Any]] = []
        for result, doc in zip(results, self._nlp.pipe(title_texts, batch_size=32)):
            for chunk in doc.noun_chunks:
                label = chunk.text.strip()

                if " " not in label or len(label) < 5:
                    continue
                if chunk.root.is_stop:
                    continue
                records.append({
                    "text":        label,
                    "entity_type": "topic",
                    "result_url":  result.get("url", ""),
                    "platform":    result.get("platform", ""),
                    "in_title":    True,
                })
        return records

    def _topics_from_titles(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:

        records: list[dict[str, Any]] = []
        for result in results:
            title = result.get("title", "")
            words = [
                w for w in re.findall(r"[a-zA-Z]{3,}", title.lower())
                if w not in _BIGRAM_STOPWORDS
            ]
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                records.append({
                    "text":        bigram,
                    "entity_type": "topic",
                    "result_url":  result.get("url", ""),
                    "platform":    result.get("platform", ""),
                    "in_title":    True,
                })
        return records

    @staticmethod
    def _deduplicate(
        records: list[dict[str, Any]],
        prefix:  str = "entity",
    ) -> dict[str, dict[str, Any]]:

        buckets: dict[str, dict[str, Any]] = {}
        for rec in records:
            norm = rec["text"].lower().strip()
            if not norm or len(norm) < _MIN_LABEL_LEN:
                continue
            if norm not in buckets:
                node_id = f"{prefix}-{_short_hash(norm)}"
                buckets[norm] = {
                    "id":          node_id,
                    "label":       rec["text"],
                    "entity_type": rec["entity_type"],
                    "count":       0,
                    "platforms":   [],
                    "urls":        [],
                    "title_hits":  0,
                }
            entry = buckets[norm]
            entry["count"] += 1
            if rec["result_url"] and rec["result_url"] not in entry["urls"]:
                entry["urls"].append(rec["result_url"])
            if rec["platform"] and rec["platform"] not in entry["platforms"]:
                entry["platforms"].append(rec["platform"])
            if rec.get("in_title"):
                entry["title_hits"] += 1
        return buckets

    @staticmethod
    def _merge_maps(
        entity_map: dict[str, Any],
        topic_map:  dict[str, Any],
    ) -> dict[str, Any]:

        merged = dict(topic_map)
        for norm, entry in entity_map.items():
            if norm in merged:

                merged[norm]["count"]     += entry["count"]
                merged[norm]["entity_type"] = entry["entity_type"]
                for url in entry["urls"]:
                    if url not in merged[norm]["urls"]:
                        merged[norm]["urls"].append(url)
            else:
                merged[norm] = entry
        return merged

    def _build_nodes(
        self,
        query:       str,
        top_entities: list[dict[str, Any]],
        results:     list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:

        nodes: list[dict[str, Any]] = []
        lookup: dict[str, str]      = {}

        query_id = "query-root"
        nodes.append({
            "id":   query_id,
            "type": "queryNode",
            "position": {"x": 0, "y": 0},
            "data": {
                "label":     query or "Research Query",
                "nodeType":  "query",
                "count":     len(results),
                "platforms": [],
                "urls":      [],
                "color":     _TYPE_COLOR["query"],
            },
        })
        if query:
            lookup[query.lower().strip()] = query_id

        for entry in top_entities:
            if entry["count"] < self.min_entity_freq:
                continue
            etype  = entry["entity_type"]
            color  = _TYPE_COLOR.get(etype, _TYPE_COLOR["unknown"])
            rf_type = _rf_node_type(etype)
            nodes.append({
                "id":   entry["id"],
                "type": rf_type,
                "position": {"x": 0, "y": 0},
                "data": {
                    "label":     entry["label"],
                    "nodeType":  etype,
                    "count":     entry["count"],
                    "platforms": entry["platforms"],
                    "urls":      entry["urls"][:5],
                    "color":     color,
                    "titleHits": entry.get("title_hits", 0),
                },
            })
            lookup[entry["label"].lower().strip()] = entry["id"]

        platforms = sorted({r.get("platform", "") for r in results if r.get("platform")})
        for plat in platforms:
            pid = f"platform-{_short_hash(plat.lower())}"
            nodes.append({
                "id":   pid,
                "type": "platformNode",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label":    plat,
                    "nodeType": "platform",
                    "count":    sum(1 for r in results if r.get("platform") == plat),
                    "platforms": [plat],
                    "urls":     [],
                    "color":    _TYPE_COLOR["platform"],
                },
            })
            lookup[plat.lower()] = pid

        return nodes, lookup

    def _build_edges(
        self,
        query:          str,
        top_entities:   list[dict[str, Any]],
        entity_records: list[dict[str, Any]],
        results:        list[dict[str, Any]],
        node_lookup:    dict[str, str],
    ) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]]                = []
        edge_weights: dict[tuple[str, str], int]   = Counter()
        edge_relations: dict[tuple[str, str], str] = {}

        query_id    = "query-root"
        entity_ids  = {e["id"] for e in top_entities}

        for entry in top_entities:
            if entry["id"] not in entity_ids:
                continue
            key = (query_id, entry["id"])
            edge_weights[key]   = entry["count"]
            edge_relations[key] = "related_to"

        for rec in entity_records:
            eid  = node_lookup.get(rec["text"].lower().strip())
            plat = rec.get("platform", "").lower()
            pid  = node_lookup.get(plat)
            if eid and pid and eid != pid:
                key = (eid, pid)
                edge_weights[key]    += 1
                edge_relations[key]   = "found_on"

        url_to_entities: dict[str, list[str]] = defaultdict(list)
        for rec in entity_records:
            eid = node_lookup.get(rec["text"].lower().strip())
            if eid:
                url_to_entities[rec["result_url"]].append(eid)

        for url, eids in url_to_entities.items():
            unique = list(dict.fromkeys(eids))
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    a, b = unique[i], unique[j]

                    key = (a, b) if a < b else (b, a)
                    edge_weights[key] += 1
                    edge_relations.setdefault(key, "co_occurs_with")

        if self._nlp:
            dep_edges = self._extract_dep_relations(results, node_lookup)
            for (src, tgt, relation) in dep_edges:
                key = (src, tgt) if src < tgt else (tgt, src)
                edge_weights[key]  = edge_weights.get(key, 0) + 1
                edge_relations[key] = relation

        all_node_ids = set(node_lookup.values())
        seen_pairs: set[frozenset[str]] = set()

        for (src, tgt), weight in edge_weights.items():
            pair = frozenset({src, tgt})
            if pair in seen_pairs or src == tgt:
                continue
            if src not in all_node_ids or tgt not in all_node_ids:
                continue
            seen_pairs.add(pair)

            relation  = edge_relations.get((src, tgt)) or edge_relations.get((tgt, src), "related_to")
            is_root   = src == query_id or tgt == query_id
            rf_type   = _EDGE_TYPES.get(relation, "default")

            edges.append({
                "id":       f"e-{_short_hash(f'{src}{tgt}')}",
                "source":   src,
                "target":   tgt,
                "type":     rf_type,
                "label":    relation.replace("_", " "),
                "animated": is_root,
                "data": {
                    "relation":    relation,
                    "weight":      weight,
                    "strokeWidth": min(1 + weight, 6),
                },
            })

        return edges

    def _extract_dep_relations(
        self,
        results:     list[dict[str, Any]],
        node_lookup: dict[str, str],
    ) -> list[tuple[str, str, str]]:

        found: list[tuple[str, str, str]] = []
        texts  = [f"{r.get('title', '')}. {r.get('snippet', '')}" for r in results]

        for doc in self._nlp.pipe(texts, batch_size=32):
            for token in doc:
                if token.pos_ != "VERB" or token.dep_ != "ROOT":
                    continue
                subjects = [w for w in token.lefts  if w.dep_ in _RICH_DEPS]
                objects  = [w for w in token.rights if w.dep_ in _RICH_DEPS]
                if not subjects or not objects:
                    continue
                for subj in subjects[:1]:
                    for obj in objects[:1]:
                        sid = node_lookup.get(subj.text.lower().strip())
                        oid = node_lookup.get(obj.text.lower().strip())
                        if sid and oid and sid != oid:
                            verb = token.lemma_.lower()
                            found.append((sid, oid, verb[:20]))
        return found

    @staticmethod
    def _apply_layout(
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:

        query_id    = "query-root"
        platforms   = [n for n in nodes if n["data"]["nodeType"] == "platform"]
        entities    = [n for n in nodes if n["id"] != query_id
                       and n["data"]["nodeType"] != "platform"]

        tier1 = [n for n in entities if n["data"]["count"] >= 5]
        tier2 = [n for n in entities if 2 <= n["data"]["count"] < 5]
        tier3 = [n for n in entities if n["data"]["count"] < 2]

        def place_ring(
            ring_nodes: list[dict[str, Any]],
            radius:     float,
            angle_offset: float = 0.0,
        ) -> None:
            total = len(ring_nodes)
            if total == 0:
                return
            for i, node in enumerate(ring_nodes):
                angle = angle_offset + (2 * math.pi * i) / total
                node["position"] = {
                    "x": round(radius * math.cos(angle)),
                    "y": round(radius * math.sin(angle)),
                }

        place_ring(tier1,     280, angle_offset=0.0)
        place_ring(tier2,     500, angle_offset=math.pi / max(len(tier1), 1))
        place_ring(tier3,     700, angle_offset=0.3)
        place_ring(platforms, 900, angle_offset=math.pi / 4)

    @staticmethod
    def _empty_graph(query: str, t0: float) -> dict[str, Any]:
        return {
            "nodes": [],
            "edges": [],
            "metadata": {
                "total_results": 0, "total_nodes": 0, "total_edges": 0,
                "node_types": {}, "platforms": [], "spacy_active": _SPACY_OK,
                "extraction_ms": 0,
            },
        }

def _short_hash(text: str) -> str:

    return hashlib.md5(text.encode()).hexdigest()[:8]

def _rf_node_type(entity_type: str) -> str:

    mapping = {
        "query":        "queryNode",
        "topic":        "topicNode",
        "organization": "orgNode",
        "person":       "personNode",
        "technology":   "techNode",
        "concept":      "conceptNode",
        "location":     "locationNode",
        "platform":     "platformNode",
    }
    return mapping.get(entity_type, "topicNode")

if __name__ == "__main__":
    import json

    gs = GraphService(min_entity_freq=1, max_nodes=40)

    dummy_results = [
        {
            "title":      "Attention Is All You Need",
            "snippet":    "Google Brain researchers Vaswani et al. propose the Transformer "
                          "architecture, replacing RNNs with self-attention for NLP tasks.",
            "url":        "https://arxiv.org/abs/1706.03762",
            "platform":   "Arxiv",
            "engagement": 0,
        },
        {
            "title":      "OpenAI releases GPT-4 with multimodal capabilities",
            "snippet":    "OpenAI's GPT-4 model supports text and image inputs, outperforming "
                          "GPT-3 on benchmarks including MMLU and HumanEval.",
            "url":        "https://openai.com/gpt-4",
            "platform":   "News",
            "engagement": 1500,
        },
        {
            "title":      "Hugging Face Transformers library hits 100k GitHub stars",
            "snippet":    "The Hugging Face Transformers library, widely used for BERT, GPT, "
                          "and T5 fine-tuning, has crossed 100k stars on GitHub.",
            "url":        "https://github.com/huggingface/transformers",
            "platform":   "GitHub",
            "engagement": 2300,
        },
        {
            "title":      "LLaMA 2: Meta's open-source LLM for research",
            "snippet":    "Meta AI releases LLaMA 2, a large language model available for "
                          "academic and commercial use, competing with GPT-4 and Claude.",
            "url":        "https://arxiv.org/abs/2307.09288",
            "platform":   "Arxiv",
            "engagement": 0,
        },
        {
            "title":      "How do I fine-tune BERT for text classification?",
            "snippet":    "You can fine-tune BERT using the Hugging Face Transformers library. "
                          "Load the model, add a classification head, and train on your dataset.",
            "url":        "https://stackoverflow.com/q/99999",
            "platform":   "StackOverflow",
            "engagement": 180,
        },
    ]

    graph = gs.build_graph(dummy_results, query="transformer LLM architecture")

    meta = graph["metadata"]
    print(f"\nExtraction engine : {'spaCy ' + spacy.__version__ if _SPACY_OK else 'regex fallback'}")
    print(f"Results processed : {meta['total_results']}")
    print(f"Nodes created     : {meta['total_nodes']}")
    print(f"Edges created     : {meta['total_edges']}")
    print(f"Extraction time   : {meta['extraction_ms']} ms")
    print(f"\nNode type breakdown:")
    for t, n in sorted(meta["node_types"].items(), key=lambda x: -x[1]):
        print(f"  {t:<16} {n}")

    print(f"\nTop 5 nodes by count:")
    entity_nodes = [n for n in graph["nodes"] if n["data"]["nodeType"] not in ("query", "platform")]
    for n in sorted(entity_nodes, key=lambda x: -x["data"]["count"])[:5]:
        d = n["data"]
        print(f"  [{d['nodeType']:<14}] {d['label']:<35} count={d['count']}  "
              f"pos=({n['position']['x']:>5}, {n['position']['y']:>5})")

    print(f"\nSample edges:")
    for e in graph["edges"][:6]:
        print(f"  {e['source'][:18]:<20} --[{e['label']:<18}]--> {e['target'][:18]}")

    print(f"\nReact Flow JSON (truncated):")
    sample = {
        "nodes": graph["nodes"][:2],
        "edges": graph["edges"][:2],
    }
    print(json.dumps(sample, indent=2))
