from typing import Any, Dict, List

import httpx


class WebSearchTool:
    name = "web_search_tool"

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        # Lightweight no-key search via DuckDuckGo instant answer API.
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return {"success": False, "error": f"Search failed: {exc}"}

        results: List[Dict[str, str]] = []
        abstract = data.get("AbstractText")
        if abstract:
            results.append({"title": data.get("Heading") or "Summary", "snippet": abstract, "url": data.get("AbstractURL", "")})
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                results.append({"title": item.get("Text", "")[:80], "snippet": item.get("Text", ""), "url": item.get("FirstURL", "")})

        return {"success": True, "query": query, "results": results[:max_results]}

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        if action != "web_search":
            return {"success": False, "error": f"Unsupported web action: {action}"}
        return self.search(kwargs["query"], kwargs.get("max_results", 5))

