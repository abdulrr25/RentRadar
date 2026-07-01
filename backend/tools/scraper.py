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


async def _search(prompt: str, source_name: str, limit: int = 6) -> dict:
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
                return {"source": source_name, "status": "error", "results": [],
                        "error": "No results returned by search API"}

            return {"source": source_name, "status": "ok", "results": results}
    except Exception as e:
        return {"source": source_name, "status": "error", "results": [], "error": str(e)}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Search NoBroker for real listings in this locality.

    NOTE: We intentionally do NOT include the budget in the query.
    Putting ₹{max_rent} in the search string means Anakin returns pages
    that *mention* that number (could be deposit, comparison, unrelated text),
    and _extract_price() then picks that number up as the rent — creating
    artificially correct-looking but wrong prices.  Letting the search engine
    return genuine property pages and reading the actual price from each
    snippet gives far more reliable results.
    """
    prompt = f'{bhk} flat for rent in {locality} Bangalore site:nobroker.in'
    return await _search(prompt, "NoBroker")


async def fetch_olx(locality: str, bhk: str, max_rent: int) -> dict:
    """Search OLX for rental ads in this locality."""
    prompt = f'{bhk} for rent {locality} Bangalore site:olx.in'
    return await _search(prompt, "OLX")


async def fetch_housing(locality: str, bhk: str, max_rent: int) -> dict:
    """Search Housing.com for rental listings in this locality."""
    prompt = f'{bhk} rental flat {locality} Bangalore site:housing.com'
    return await _search(prompt, "Housing.com")
