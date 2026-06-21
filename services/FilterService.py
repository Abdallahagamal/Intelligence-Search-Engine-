

from __future__ import annotations

import html
import re
import string
import unicodedata
from collections import Counter
from typing import Any
from urllib.parse import urlparse

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _fuzz = None
    _HAS_RAPIDFUZZ = False

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "i", "me", "my", "we", "our",
    "you", "your", "he", "she", "it", "its", "they", "their", "this", "that",
    "these", "those", "to", "of", "in", "on", "at", "by", "for", "with",
    "about", "from", "as", "into", "through", "during", "what", "which",
    "who", "how", "all", "each", "every", "some", "any", "most", "other",
    "more", "so", "then", "too", "very", "just", "but", "and", "or",
    "not", "no", "if", "up", "out", "use", "used", "using",
})

_INTENT_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "comparison": [
        ("vs",            2), ("versus",         2), ("compare",        2),
        ("comparison",    2), ("difference",      2), ("differences",    2),
        ("between",       1), ("alternative",     1), ("alternatives",   1),
        ("better than",   2), ("worse than",      2), ("or",             1),
        ("pros and cons", 3), ("pros cons",       3), ("tradeoff",       2),
        ("benchmark",     2),
    ],
    "recommendation": [
        ("best",          2), ("top",             1), ("recommend",      2),
        ("recommended",   2), ("suggest",         2), ("which one",      2),
        ("should i use",  3), ("favorite",        1), ("popular",        1),
        ("worth",         1), ("pick",            1), ("choose",         1),
        ("ideal",         1), ("perfect",         1), ("top rated",      2),
    ],
    "news": [
        ("latest",        2), ("new",             1), ("recent",         2),
        ("today",         2), ("this week",       2), ("this month",     2),
        ("breaking",      2), ("update",          1), ("announcement",   2),
        ("release",       1), ("released",        1), ("just released",  3),
        ("2024",          1), ("2025",            1), ("2026",           1),
    ],
    "research": [
        ("paper",         2), ("papers",          2), ("research",       2),
        ("study",         2), ("studies",         2), ("survey",         2),
        ("arxiv",         3), ("journal",         2), ("publication",    2),
        ("experiment",    2), ("academic",        2), ("literature",     2),
        ("findings",      2), ("theory",          1), ("review",         1),
        ("doi",           3),
    ],
    "coding": [
        ("how to",        2), ("implement",       2), ("implementation", 2),
        ("function",      1), ("code",            1), ("library",        1),
        ("api",           1), ("error",           1), ("bug",            2),
        ("syntax",        2), ("tutorial",        2), ("example",        1),
        ("install",       1), ("framework",       1), ("sdk",            2),
        ("debug",         2), ("build",           1), ("deploy",         1),
        ("algorithm",     2), ("package",         1), ("snippet",        2),
        ("programming",   1), ("script",          1),
    ],
}

_EXPANSION_MAP: dict[str, list[str]] = {
    "ai":          ["artificial intelligence", "machine learning"],
    "ml":          ["machine learning", "deep learning"],
    "llm":         ["large language model", "gpt", "transformer"],
    "nlp":         ["natural language processing", "text analysis"],
    "cv":          ["computer vision", "image recognition"],
    "nn":          ["neural network", "deep learning"],
    "rl":          ["reinforcement learning"],
    "gan":         ["generative adversarial network"],
    "rag":         ["retrieval augmented generation"],
    "api":         ["rest api", "endpoint", "interface"],
    "db":          ["database", "sql"],
    "ui":          ["user interface", "frontend"],
    "ux":          ["user experience", "design"],
    "devops":      ["ci/cd", "deployment", "infrastructure"],
    "dev":         ["developer", "development"],
    "os":          ["operating system"],
    "cli":         ["command line", "terminal", "shell"],
    "best":        ["top", "recommended", "leading"],
    "tool":        ["software", "library", "framework"],
    "tools":       ["software", "libraries", "frameworks", "apps"],
    "tutorial":    ["guide", "how-to", "walkthrough", "example"],
    "compare":     ["comparison", "vs", "difference"],
    "fast":        ["performance", "efficient", "optimized"],
    "free":        ["open source", "no cost"],
    "open source": ["github", "oss"],
    "model":       ["neural network", "llm", "transformer"],
    "search":      ["retrieval", "query", "indexing"],
    "vector":      ["embedding", "similarity", "semantic"],
    "chat":        ["conversational ai", "chatbot", "llm"],
}

_INTENT_BONUS: dict[str, list[str]] = {
    "coding":         ["github", "stackoverflow", "docs", "documentation"],
    "research":       ["arxiv", "paper", "doi", "semantic scholar"],
    "news":           ["breaking", "latest", "press release"],
    "comparison":     ["benchmark", "pros cons", "side by side"],
    "recommendation": ["top rated", "review", "user review"],
}

_INTENT_CONFIG: dict[str, dict[str, Any]] = {
    "coding": {
        "min_snippet_len":  10,
        "spam_sensitivity": "low",
        "require_snippet":  False,
    },
    "research": {
        "min_snippet_len":  50,
        "spam_sensitivity": "medium",
        "require_snippet":  True,
    },
    "news": {
        "min_snippet_len":  30,
        "spam_sensitivity": "high",
        "require_snippet":  True,
    },
    "comparison": {
        "min_snippet_len":  20,
        "spam_sensitivity": "medium",
        "require_snippet":  False,
    },
    "recommendation": {
        "min_snippet_len":  20,
        "spam_sensitivity": "medium",
        "require_snippet":  True,
    },
}
_DEFAULT_CONFIG: dict[str, Any] = {
    "min_snippet_len":  20,
    "spam_sensitivity": "medium",
    "require_snippet":  False,
}

_SPAM_HIGH = re.compile(
    r"(click\s*here|earn\s*money|free\s*money|buy\s*now|limited\s*offer"
    r"|make\s*money\s*fast|guaranteed\s*results|risk[\s-]free\s*trial"
    r"|act\s*now|100\s*%\s*free|you\s*won|congratulations\s*you"
    r"|get\s*paid\s*to|work\s*from\s*home\s*make)",
    re.IGNORECASE,
)
_SPAM_MEDIUM = re.compile(
    r"(subscribe\s*now|sign\s*up\s*now|click\s*below|download\s*now"
    r"|exclusive\s*deal|don'?t\s*miss|last\s*chance|while\s*supplies\s*last"
    r"|hurry\s*up|order\s*now)",
    re.IGNORECASE,
)
_CLICKBAIT = re.compile(
    r"(you\s*won'?t\s*believe|shocking|mind[\s-]blowing|unbelievable"
    r"|this\s*is\s*why|here'?s\s*why|the\s*truth\s*about|secret\s*to"
    r"|\d+\s*reasons\s*why|\d+\s*things\s*you\s*(need|should|must)"
    r"|what\s*they\s*don'?t\s*want\s*you\s*to\s*know)",
    re.IGNORECASE,
)
_URL_SHORTENER = re.compile(
    r"(bit\.ly|tinyurl\.com|goo\.gl|ow\.ly|rb\.gy|is\.gd|buff\.ly"
    r"|dlvr\.it|ift\.tt|t\.co/[a-zA-Z0-9]{1,7}$)",
    re.IGNORECASE,
)
_HTML_TAG = re.compile(r"<[^>]+>")

class FilterService:

    def __init__(self, dup_threshold: int = 85) -> None:

        self.dup_threshold = dup_threshold

    def preprocess(self, query: str) -> dict[str, Any]:

        original = query
        cleaned  = self._clean_query(query)
        lower    = cleaned.lower()

        tokens   = lower.split()
        keywords = [t for t in tokens if t not in _STOPWORDS and len(t) > 1]

        intent, confidence = self._detect_intent(lower)
        expanded           = self._expand_keywords(keywords, intent)

        return {
            "original":          original,
            "cleaned":           cleaned,
            "intent":            intent,
            "intent_confidence": round(confidence, 3),
            "keywords":          keywords,
            "expanded_keywords": expanded,
        }

    def postfilter(
        self,
        results: list[dict[str, Any]],
        intent: str = "research",
    ) -> dict[str, Any]:

        cfg = _INTENT_CONFIG.get(intent, _DEFAULT_CONFIG)

        enriched: list[dict[str, Any]] = []
        for item in results:
            copy = dict(item)
            self._normalise_fields(copy)
            copy["quality"] = self._build_quality(copy)
            copy["flags"]   = self._build_flags(copy, cfg)
            enriched.append(copy)

        self._annotate_duplicates(enriched)

        return {
            "results":  enriched,
            "metadata": {
                "total_input":  len(results),
                "total_output": len(enriched),
            },
            "flags_summary": self._build_summary(enriched),
        }

    @staticmethod
    def _normalise_text(text: str) -> str:

        text = _HTML_TAG.sub("", text or "")
        text = html.unescape(text)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        for src, dst in (
            ("’", "'"), ("‘", "'"),
            ("“", '"'), ("”", '"'),
            ("–", "-"), ("—", "-"),
            ("…", "..."),
        ):
            text = text.replace(src, dst)
        return re.sub(r"\s+", " ", text).strip()

    def _normalise_fields(self, item: dict[str, Any]) -> None:

        for field in ("title", "snippet", "author"):
            if field in item:
                item[field] = self._normalise_text(str(item[field] or ""))

    @staticmethod
    def _clean_query(text: str) -> str:

        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        for src, dst in (
            ("’", "'"), ("‘", "'"),
            ("“", '"'), ("”", '"'),
            ("–", "-"), ("—", "-"),
            ("…", "..."),
        ):
            text = text.replace(src, dst)
        return text

    @staticmethod
    def _build_quality(item: dict[str, Any]) -> dict[str, Any]:

        title   = (item.get("title")   or "").strip()
        snippet = (item.get("snippet") or "").strip()
        url     = (item.get("url")     or "").strip()

        url_valid = False
        domain    = ""
        if url:
            try:
                parsed    = urlparse(url)
                url_valid = bool(parsed.scheme in ("http", "https") and parsed.netloc)
                domain    = re.sub(r"^www\.", "", parsed.netloc)
            except Exception:
                pass

        return {
            "has_title":      bool(title),
            "has_snippet":    bool(snippet),
            "snippet_length": len(snippet),
            "url_valid":      url_valid,
            "domain":         domain,
        }

    def _build_flags(
        self,
        item: dict[str, Any],
        cfg: dict[str, Any],
    ) -> list[dict[str, str]]:

        flags: list[dict[str, str]] = []
        title       = (item.get("title")   or "").strip()
        snippet     = (item.get("snippet") or "").strip()
        url         = (item.get("url")     or "").strip()
        quality     = item.get("quality", {})
        sensitivity = cfg.get("spam_sensitivity", "medium")

        if not url:
            flags.append({"type": "missing_url", "severity": "high"})
        elif not quality.get("url_valid"):
            flags.append({"type": "invalid_url", "severity": "high"})

        if not title:
            flags.append({"type": "missing_title", "severity": "high"})

        min_len = cfg.get("min_snippet_len", 20)
        if not snippet:
            sev = "medium" if cfg.get("require_snippet") else "low"
            flags.append({"type": "empty_snippet", "severity": sev})
        elif len(snippet) < min_len:
            flags.append({"type": "low_quality", "severity": "low"})

        if not title:
            return flags

        alpha = re.sub(r"[^a-zA-Z]", "", title)
        if len(alpha) > 8 and alpha == alpha.upper():
            flags.append({"type": "spam_allcaps", "severity": "medium"})

        punct_threshold = 0.25 if sensitivity == "high" else 0.30
        punct_ratio = sum(1 for c in title if c in string.punctuation) / max(len(title), 1)
        if punct_ratio > punct_threshold:
            flags.append({"type": "spam_punctuation", "severity": "medium"})

        if _SPAM_HIGH.search(title) or _SPAM_HIGH.search(snippet):
            flags.append({"type": "spam_content", "severity": "high"})

        if sensitivity in ("medium", "high"):
            if _SPAM_MEDIUM.search(title) or _SPAM_MEDIUM.search(snippet):
                flags.append({"type": "spam_content", "severity": "medium"})

        if _CLICKBAIT.search(title):
            clickbait_sev = "medium" if sensitivity == "high" else "low"
            flags.append({"type": "clickbait", "severity": clickbait_sev})

        if url and _URL_SHORTENER.search(url):
            flags.append({"type": "spam_url", "severity": "high"})

        return flags

    def _annotate_duplicates(self, items: list[dict[str, Any]]) -> None:

        n = len(items)
        dup_of: dict[int, int]   = {}
        scores:  dict[int, float] = {}

        for i in range(n):
            t_i = (items[i].get("title") or "").strip()
            u_i = (items[i].get("url")   or "").strip()

            best_j, best_score = -1, 0.0

            for j in range(i):
                t_j = (items[j].get("title") or "").strip()
                u_j = (items[j].get("url")   or "").strip()

                if u_i and u_j and u_i == u_j:
                    best_j, best_score = j, 100.0
                    break

                if t_i and t_j and _HAS_RAPIDFUZZ:
                    sim = float(_fuzz.token_sort_ratio(t_i, t_j))
                    if sim >= self.dup_threshold and sim > best_score:
                        best_j, best_score = j, sim

            if best_j >= 0:
                dup_of[i]  = best_j
                scores[i]  = best_score

        def root(idx: int) -> int:
            while idx in dup_of:
                idx = dup_of[idx]
            return idx

        root_to_members: dict[int, list[int]] = {}
        for i in range(n):
            root_to_members.setdefault(root(i), []).append(i)

        group_ids: dict[int, str] = {}
        gid = 0
        for members in root_to_members.values():
            if len(members) > 1:
                gid += 1
                label = f"grp_{gid}"
                for idx in members:
                    group_ids[idx] = label

        for i, item in enumerate(items):
            if i in dup_of:
                j = dup_of[i]
                item["is_duplicate"]       = True
                item["duplicate_score"]    = round(scores[i], 2)
                item["duplicate_of"]       = items[j].get("url") or f"index:{j}"
                item["duplicate_group_id"] = group_ids.get(i)
            else:
                item["is_duplicate"]       = False
                item["duplicate_score"]    = 0.0
                item["duplicate_of"]       = None
                item["duplicate_group_id"] = group_ids.get(i)

    @staticmethod
    def _build_summary(items: list[dict[str, Any]]) -> dict[str, int]:
        _SPAM_TYPES    = {"spam_content", "spam_allcaps", "spam_punctuation",
                          "spam_url", "clickbait"}
        _MISSING_TYPES = {"missing_url", "missing_title"}

        spam = dup = missing = 0
        for item in items:
            flag_types = {f["type"] for f in item.get("flags", [])}
            if flag_types & _SPAM_TYPES:
                spam    += 1
            if flag_types & _MISSING_TYPES:
                missing += 1
            if item.get("is_duplicate"):
                dup     += 1

        return {"spam": spam, "duplicates": dup, "missing_fields": missing}

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

        confidence = scores[best] / (sum(scores.values()) or 1)
        return best, confidence

    @staticmethod
    def _expand_keywords(keywords: list[str], intent: str) -> list[str]:
        seen: set[str]      = set(keywords)
        expanded: list[str] = list(keywords)

        for kw in keywords:
            for term in _EXPANSION_MAP.get(kw, []):
                if term not in seen:
                    expanded.append(term)
                    seen.add(term)

        for bonus in _INTENT_BONUS.get(intent, []):
            if bonus not in seen:
                expanded.append(bonus)
                seen.add(bonus)

        return expanded

if __name__ == "__main__":
    import json

    fs = FilterService()

    queries = [
        "best AI tools",
        "Python vs JavaScript for backend",
        "latest GPT-4 news 2025",
        "how to implement RAG with LangChain",
        "transformer attention mechanism paper arxiv",
    ]
    print("=" * 65)
    print("PREPROCESS")
    print("=" * 65)
    for q in queries:
        r = fs.preprocess(q)
        print(f"\n  Query  : {r['original']}")
        print(f"  Intent : {r['intent']}  (conf={r['intent_confidence']})")
        print(f"  Keys   : {r['keywords']}")
        print(f"  Exp+   : {r['expanded_keywords'][:5]} ...")

    dummy = [

        {"title": "OpenAI releases GPT-5",
         "snippet": "OpenAI has announced GPT-5 with dramatically improved reasoning.",
         "url": "https://openai.com/gpt5", "platform": "News",
         "date": "2025-05-01", "author": "Sam Altman", "engagement": 1200},

        {"title": "GPT-5 Released by OpenAI",
         "snippet": "OpenAI releases its next flagship model.",
         "url": "https://techcrunch.com/gpt5", "platform": "News",
         "date": "2025-05-01", "author": "Reporter", "engagement": 800},

        {"title": "OpenAI GPT-5 Announcement",
         "snippet": "Details on the new model.",
         "url": "https://openai.com/gpt5", "platform": "News",
         "date": "2025-05-01", "author": "", "engagement": 0},

        {"title": "Some Article", "snippet": "Content here.", "url": "",
         "platform": "Reddit", "date": "", "author": "", "engagement": 5},

        {"title": "CLICK HERE FREE MONEY!!!",
         "snippet": "Earn money fast guaranteed results.",
         "url": "https://spam.io/free", "platform": "News",
         "date": "", "author": "", "engagement": 0},

        {"title": "Interesting Research on Transformers",
         "snippet": "A deep dive into self-attention heads and their visualisation.",
         "url": "https://bit.ly/abc123", "platform": "News",
         "date": "", "author": "", "engagement": 50},

        {"title": "10 Things You Must Know About LLMs",
         "snippet": "You won't believe what these language models can do.",
         "url": "https://blog.example.com/llms", "platform": "Blog",
         "date": "2025-04-10", "author": "Blogger", "engagement": 30},

        {"title": "asyncio.gather example",
         "snippet": "Use asyncio.gather(*coros).",
         "url": "https://stackoverflow.com/q/123", "platform": "StackOverflow",
         "date": "2023-01-01", "author": "user42", "engagement": 55},

        {"title": "Attention Is All You Need",
         "snippet": "We propose the Transformer, a model architecture based solely on attention.",
         "url": "https://arxiv.org/abs/1706.03762", "platform": "Arxiv",
         "date": "2017-06-12", "author": "Vaswani et al.", "engagement": 0},
    ]

    print("\n" + "=" * 65)
    print("POSTFILTER  (intent=news)")
    print("=" * 65)
    out = fs.postfilter(dummy, intent="news")
    print(f"\n  Input items  : {out['metadata']['total_input']}")
    print(f"  Output items : {out['metadata']['total_output']}  (nothing removed)")
    print(f"  Flags summary: {out['flags_summary']}")
    print()
    for r in out["results"]:
        dup_tag  = f" [DUP grp={r['duplicate_group_id']} score={r['duplicate_score']}]" \
                   if r["is_duplicate"] else ""
        flag_tag = ", ".join(f"{f['type']}:{f['severity']}" for f in r["flags"]) or "ok"
        domain   = r["quality"]["domain"] or "—"
        print(f"  [{r.get('platform','?'):12}] {r['title'][:45]:<45}  "
              f"flags=[{flag_tag}]  domain={domain}{dup_tag}")
