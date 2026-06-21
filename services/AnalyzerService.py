from __future__ import annotations

import asyncio
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, quote_plus

import httpx

class AnalyzerService:
   
    _EMPTY: dict[str, Any] = {
        "title": "",
        "snippet": "",
        "url": "",
        "platform": "",
        "date": "",
        "author": "",
        "engagement": 0,
    }

    _SOURCE_MAP: dict[str, str] = {

        "github":        "_fetch_github",
        "arxiv":         "_fetch_arxiv",
        "stackoverflow": "_fetch_stackoverflow",
        "wikipedia":     "_fetch_wikipedia",
        "news":          "_fetch_news",
    }

    def __init__(
        self,
        timeout: float = 10.0,
        news_api_key: str = "",
        github_token: str = "",
    ) -> None:
        self.timeout = httpx.Timeout(timeout)
        self.news_api_key = news_api_key
        self.github_token = github_token

   

    def _norm(self, **kwargs: Any) -> dict[str, Any]:
       
        result = dict(self._EMPTY)
        result.update(kwargs)
        try:
            result["engagement"] = int(result["engagement"] or 0)
        except (TypeError, ValueError):
            result["engagement"] = 0
        result["snippet"] = (result["snippet"] or "")[:500]
        result["title"]   = (result["title"]   or "").strip()
        result["author"]  = (result["author"]  or "").strip()
        return result

    @staticmethod
    def _unix_to_iso(ts: Any) -> str:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except Exception:
            return ""

    @staticmethod
    def _strip_html(text: str) -> str:
       
        return html.unescape(re.sub(r"<[^>]+>", "", text or ""))

   

    async def _fetch_reddit(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        url = (
            "https://www.reddit.com/search.json"
            f"?q={quote_plus(query)}&sort=relevance&limit=10&type=link"
        )
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0 Safari/537.36",
        "Accept": "application/json",
    }
        r = await client.get(url)
        r.raise_for_status()
        results = []
        for post in r.json()["data"]["children"]:
            d = post["data"]
            results.append(self._norm(
                title=d.get("title", ""),
                snippet=d.get("selftext", "") or d.get("url", ""),
                url=f"https://reddit.com{d.get('permalink', '')}",
                platform="Reddit",
                date=self._unix_to_iso(d.get("created_utc", 0)),
                author=d.get("author", ""),
                engagement=d.get("score", 0),
            ))
        return results

    async def _fetch_github(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        url = (
            "https://api.github.com/search/repositories"
            f"?q={quote_plus(query)}&sort=stars&per_page=10"
        )
        extra: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            extra["Authorization"] = f"Bearer {self.github_token}"
        r = await client.get(url, headers=extra)
        r.raise_for_status()
        results = []
        for item in r.json().get("items", []):
            results.append(self._norm(
                title=item.get("full_name", ""),
                snippet=item.get("description", "") or "",
                url=item.get("html_url", ""),
                platform="GitHub",
                date=item.get("updated_at", ""),
                author=(item.get("owner") or {}).get("login", ""),
                engagement=item.get("stargazers_count", 0),
            ))
        return results

    async def _fetch_arxiv(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{quote_plus(query)}&max_results=10&sortBy=relevance"
        )
        r = await client.get(url)
        r.raise_for_status()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(r.text)
        results = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").replace("\n", " ").strip()
            summary = (entry.findtext("atom:summary", "", ns) or "").replace("\n", " ").strip()
            link = (entry.findtext("atom:id", "", ns) or "").strip()
            published = entry.findtext("atom:published", "", ns) or ""
            author_els = entry.findall("atom:author", ns)
            first_author = ""
            if author_els:
                first_author = author_els[0].findtext("atom:name", "", ns) or ""
            results.append(self._norm(
                title=title,
                snippet=summary,
                url=link,
                platform="Arxiv",
                date=published,
                author=first_author,
                engagement=0,
            ))
        return results

    async def _fetch_stackoverflow(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        url = (
            "https://api.stackexchange.com/2.3/search"
            f"?order=desc&sort=relevance&intitle={quote_plus(query)}"
            "&site=stackoverflow&pagesize=10"
        )
        r = await client.get(url)
        r.raise_for_status()
        results = []
        for item in r.json().get("items", []):
            results.append(self._norm(
                title=item.get("title", ""),
                snippet=", ".join(item.get("tags", [])),
                url=item.get("link", ""),
                platform="StackOverflow",
                date=self._unix_to_iso(item.get("creation_date", 0)),
                author=(item.get("owner") or {}).get("display_name", ""),
                engagement=item.get("score", 0),
            ))
        return results

    async def _fetch_wikipedia(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote_plus(query)}"
            "&srlimit=10&utf8=1&format=json&srprop=snippet|timestamp|wordcount"
        )
        r = await client.get(url)
        r.raise_for_status()
        results = []
        for item in r.json().get("query", {}).get("search", []):
            page_id = item.get("pageid", "")
            results.append(self._norm(
                title=item.get("title", ""),
                snippet=re.sub(r"<[^>]+>", "", item.get("snippet", "")),
                url=f"https://en.wikipedia.org/?curid={page_id}",
                platform="Wikipedia",
                date=item.get("timestamp", ""),
                author="",
                engagement=item.get("wordcount", 0),
            ))
        return results

    async def _fetch_news(
        self, client: httpx.AsyncClient, query: str
    ) -> list[dict[str, Any]]:
        
        if not self.news_api_key:
            raise RuntimeError(
                "News API key not configured. "
                "Get a free key at https://newsapi.org and pass it as "
                "AnalyzerService(news_api_key='YOUR_KEY')."
            )
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={quote_plus(query)}&sortBy=relevancy&pageSize=10"
            f"&apiKey={self.news_api_key}"
        )
        r = await client.get(url)
        r.raise_for_status()
        results = []
        for article in r.json().get("articles", []):
            results.append(self._norm(
                title=article.get("title", "") or "",
                snippet=article.get("description", "") or "",
                url=article.get("url", "") or "",
                platform="News",
                date=article.get("publishedAt", "") or "",
                author=article.get("author", "") or "",
                engagement=0,
            ))
        return results

   

    async def fetch_all(
        self,
        query: str,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
       
        if sources is None:
            sources = list(self._SOURCE_MAP.keys())

        active = [s.lower() for s in sources if s.lower() in self._SOURCE_MAP]

        base_headers = {
            "User-Agent": "AnalyzerService/1.0 (multi-source search aggregator)",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=base_headers,
            follow_redirects=True,
        ) as client:
            tasks = {
                name: asyncio.create_task(
                    getattr(self, self._SOURCE_MAP[name])(client, query)
                )
                for name in active
            }
            settled = await asyncio.gather(*tasks.values(), return_exceptions=True)

        by_source: dict[str, list[dict]] = {}
        errors:    dict[str, str]        = {}
        flat:      list[dict]            = []

        for name, outcome in zip(tasks.keys(), settled):
            if isinstance(outcome, Exception):
                errors[name]    = f"{type(outcome).__name__}: {outcome}"
                by_source[name] = []
            else:
                by_source[name] = outcome
                flat.extend(outcome)

        return {"results": flat, "by_source": by_source, "errors": errors}

if __name__ == "__main__":
    import json

    async def _demo() -> None:
        service = AnalyzerService(timeout=12.0)
        query   = "transformer neural network"
        output  = await service.fetch_all(query, sources=["reddit", "github", "arxiv",
                                                           "stackoverflow", "wikipedia"])
        print(f"\nQuery: '{query}'")
        print(f"Total results : {len(output['results'])}")
        print(f"Errors        : {output['errors'] or 'none'}\n")
        for source, items in output["by_source"].items():
            print(f"  {source:>15} → {len(items)} result(s)")
        if output["results"]:
            print("\nFirst result:\n", json.dumps(output["results"][0], indent=2))

    asyncio.run(_demo())
