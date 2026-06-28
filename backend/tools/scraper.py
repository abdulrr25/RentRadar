"""
Property listing fetcher — uses Anakin's /v1/search API to find real listings
from NoBroker, OLX, and Housing.com.

Direct scraping of these portals is blocked by bot detection, so we use web
search. Each portal returns several distinct result pages, each with its own
URL + snippet (often containing real prices) — we return ALL of them so the
agent can build a diverse, multi-platform listing set and link each listing to
its specific page.
"""

import httpx
import os

SEARCH_URL = "https://api.anakin.io/v1/search"


def _headers() -> dict:
    return {
        "X-API-Key": os.getenv("ANAKIN_API_KEY", ""),
        "Content-Type": "application/json",
    }


async def _search(prompt: str, source_name: str, limit: int = 5) -> dict:
    """
    Run an Anakin web search and return a list of structured results.

    Returns {source, status, results:[{title, url, snippet}]}. Each result is a
    distinct portal page — the agent picks listings from across all of them.
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                SEARCH_URL,
                headers=_headers(),
                json={"prompt": prompt, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            results = [
                {
                    "title": (r.get("title") or "").strip(),
                    "url": r.get("url"),
                    "snippet": (r.get("snippet") or "").strip(),
                }
                for r in data.get("results", [])
                if r.get("snippet") and r.get("url")
            ]

            if not results:
                return {"source": source_name, "status": "error", "results": []}

            return {"source": source_name, "status": "ok", "results": results}
    except Exception as e:
        return {"source": source_name, "status": "error", "results": [], "error": str(e)}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Search NoBroker individual property pages via Anakin web search.
    Targeting /property/ paths returns single-listing detail pages rather than
    category/search pages, so each URL links to one specific ad.
    """
    prompt = (
        f'site:nobroker.in/property {bhk} rent {locality} Bangalore '
        f'₹{max_rent} per month owner'
    )
    return await _search(prompt, "NoBroker", limit=6)


async def fetch_olx(locality: str, bhk: str, max_rent: int) -> dict:
    """Search OLX individual ad pages.
    OLX ad URLs contain /item/ — including that in the query pushes the search
    engine to return individual ads rather than category listing pages.
    """
    prompt = (
        f'site:olx.in/item {bhk} for rent {locality} Bangalore '
        f'₹{max_rent} month furnished'
    )
    return await _search(prompt, "OLX", limit=6)


async def fetch_housing(locality: str, bhk: str) -> dict:
    """Search Housing.com individual property detail pages.
    /rent/property-detail paths are single-property pages with exact price shown.
    """
    prompt = (
        f'site:housing.com {bhk} for rent {locality} Bangalore '
        f'rent deposit semifurnished'
    )
    return await _search(prompt, "Housing.com", limit=6)
