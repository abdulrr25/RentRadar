"""
Wire (Holocron) tool — pre-built structured actions via Anakin's /v1/holocron/task endpoint.
Covers: Reddit, Google Trends, Hacker News, Twitter/X.
"""

import httpx
import os

ANAKIN_API_KEY = os.getenv("ANAKIN_API_KEY")
HOLOCRON_BASE = "https://api.anakin.io/v1/holocron"

HEADERS = {
    "X-API-Key": ANAKIN_API_KEY or "",
    "Content-Type": "application/json",
}


async def holocron_action(action_id: str, params: dict, source_name: str) -> dict:
    """Generic Wire (Holocron) action caller — always returns a safe dict."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{HOLOCRON_BASE}/task",
                headers=HEADERS,
                json={"action_id": action_id, "params": params},
            )
            response.raise_for_status()
            data = response.json()
            return {"source": source_name, "status": "ok", "data": data}
    except Exception as e:
        return {"source": source_name, "status": "error", "data": str(e)}


async def fetch_reddit(locality: str, bhk: str) -> dict:
    """Wire → reddit.search for tenant reviews and locality discussions."""
    query = f"{locality} Bangalore rent {bhk} review"
    return await holocron_action(
        action_id="reddit.search",
        params={"query": query, "limit": 15, "sort": "relevance"},
        source_name="Reddit",
    )


async def fetch_google_trends(locality: str) -> dict:
    """Wire → google_trends.search for rental demand signals."""
    return await holocron_action(
        action_id="google_trends.search",
        params={"keyword": f"{locality} rent Bangalore", "geo": "IN-KA"},
        source_name="Google Trends",
    )


async def fetch_hackernews(locality: str) -> dict:
    """Wire → hackernews.search for tech-worker perspectives on the area."""
    return await holocron_action(
        action_id="hackernews.search",
        params={"query": f"Bangalore {locality} living"},
        source_name="Hacker News",
    )


async def fetch_twitter(locality: str) -> dict:
    """Wire → twitter.search for recent real-time chatter."""
    return await holocron_action(
        action_id="twitter.search",
        params={"query": f"{locality} Bangalore rent flat", "limit": 10},
        source_name="Twitter/X",
    )
