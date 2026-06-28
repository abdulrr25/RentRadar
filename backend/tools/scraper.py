"""
Property listing fetcher — uses Anakin's /v1/search API to find real listings
from NoBroker, OLX, and Housing.com.

Direct scraping of these portals is blocked by bot detection, so we use web
search which returns clean snippets WITH the real listing URL — letting the
UI link straight through to the original ad page.
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
    Run an Anakin web search and return clean snippets plus the top result URL.

    The returned dict carries a top-level `url` so the agent can attach a
    clickable link to each listing it surfaces from this source.
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
            results = [r for r in data.get("results", []) if r.get("snippet")]

            if not results:
                # Honest status — don't pretend a dead source returned data
                return {"source": source_name, "status": "error",
                        "data": "no results", "url": None}

            snippets = "\n\n".join(
                f"[{r.get('date', '')}] {r.get('snippet', '')}"
                for r in results
            )
            top_url = results[0].get("url")
            return {"source": source_name, "status": "ok",
                    "data": snippets, "url": top_url}
    except Exception as e:
        return {"source": source_name, "status": "error",
                "data": str(e), "url": None}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Search NoBroker listings via Anakin web search."""
    prompt = (
        f"{bhk} flat for rent in {locality} Bangalore under Rs {max_rent} "
        f"site:nobroker.in owner direct deposit price"
    )
    return await _search(prompt, "NoBroker", limit=5)


async def fetch_olx(locality: str, bhk: str, max_rent: int) -> dict:
    """Search OLX listings via Anakin web search (replaces MagicBricks, which
    Anakin's search index does not cover)."""
    prompt = (
        f"{bhk} for rent {locality} Bangalore under Rs {max_rent} "
        f"site:olx.in rent price"
    )
    return await _search(prompt, "OLX", limit=5)


async def fetch_housing(locality: str, bhk: str) -> dict:
    """Search Housing.com listings via Anakin web search."""
    prompt = (
        f"{bhk} rental flat {locality} Bangalore "
        f"site:housing.com rent price deposit"
    )
    return await _search(prompt, "Housing.com", limit=5)
