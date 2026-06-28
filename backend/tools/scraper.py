"""
Property listing fetcher — uses Anakin's /v1/search API to find real listings
from NoBroker, MagicBricks, and Housing.com.

Direct scraping of these portals is blocked by bot detection.
Web search returns clean snippets with real prices and availability.
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
    """Run an Anakin web search and return clean snippets."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                SEARCH_URL,
                headers=_headers(),
                json={"prompt": prompt, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            # Extract just the snippet text from each result
            results = data.get("results", [])
            snippets = "\n\n".join(
                f"[{r.get('date', '')}] {r.get('snippet', '')}"
                for r in results
                if r.get("snippet")
            )
            return {"source": source_name, "status": "ok", "data": snippets}
    except Exception as e:
        return {"source": source_name, "status": "error", "data": str(e)}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Search NoBroker listings via Anakin web search."""
    prompt = (
        f"{bhk} flat for rent in {locality} Bangalore under Rs {max_rent} "
        f"site:nobroker.in owner direct deposit price"
    )
    return await _search(prompt, "NoBroker", limit=5)


async def fetch_magicbricks(locality: str, bhk: str, max_rent: int) -> dict:
    """Search MagicBricks listings via Anakin web search."""
    prompt = (
        f"{bhk} apartment for rent {locality} Bangalore below Rs {max_rent} "
        f"site:magicbricks.com rent price"
    )
    return await _search(prompt, "MagicBricks", limit=5)


async def fetch_housing(locality: str, bhk: str) -> dict:
    """Search Housing.com listings via Anakin web search."""
    prompt = (
        f"{bhk} rental flat {locality} Bangalore 2024 "
        f"site:housing.com rent price deposit"
    )
    return await _search(prompt, "Housing.com", limit=5)
