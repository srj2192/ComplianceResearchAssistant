"""
Web search tool: uses Tavily API to search for latest regulatory updates,
enforcement actions, and guidance documents.
"""

import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set in .env")
        _client = TavilyClient(api_key=api_key)
    return _client


def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for latest regulatory guidance and updates.
    Returns list of {"title": str, "url": str, "content": str}
    """
    client = _get_client()

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_domains=[
            "edpb.europa.eu",
            "ico.org.uk",
            "gdpr-info.eu",
            "iso.org",
            "enisa.europa.eu",
            "ec.europa.eu",
            "nist.gov",
        ],
    )

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        })

    return results


def format_results(results: list[dict]) -> str:
    """Format web search results into a readable string for the LLM."""
    if not results:
        return "No web results found."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[Web Result {i}: {r['title']}]\nURL: {r['url']}\n{r['content']}"
        )
    return "\n\n---\n\n".join(formatted)
