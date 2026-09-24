"""
Area-sentiment fetchers — Reddit, Hacker News, Google News.

These used to go through Anakin's Wire API (see git history: holocron.py),
which billed per call same as the listing search. None of the three actually
need a paid intermediary — each has a free path of its own:
  - Reddit:       official OAuth API (client-credentials, read-only)
  - Hacker News:  Algolia's public HN Search API (no key, no auth)
  - Google News:  public RSS search feed (no key, no auth)
"""

import logging
import time
import xml.etree.ElementTree as ET

import httpx
import os

logger = logging.getLogger("rentradar.sentiment_sources")

USER_AGENT = "RentRadar/1.0 (Bangalore rental search tool)"


# ── Reddit ───────────────────────────────────────────────────────────────────

REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"

# Module-level so the access token (valid ~1hr) is reused across requests
# instead of fetched fresh every search.
_reddit_token_cache = {"token": None, "expires_at": 0.0}


async def _reddit_token(client: httpx.AsyncClient) -> str:
    if _reddit_token_cache["token"] and time.monotonic() < _reddit_token_cache["expires_at"]:
        return _reddit_token_cache["token"]

    resp = await client.post(
        REDDIT_TOKEN_URL,
        auth=(os.getenv("REDDIT_CLIENT_ID", ""), os.getenv("REDDIT_CLIENT_SECRET", "")),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()
    _reddit_token_cache["token"] = data["access_token"]
    _reddit_token_cache["expires_at"] = time.monotonic() + data.get("expires_in", 3600) - 60
    return _reddit_token_cache["token"]


async def fetch_reddit(locality: str, bhk: str) -> dict:
    """Reddit's official free API — r/bangalore posts about this locality."""
    query = f"{locality} rent {bhk}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            token = await _reddit_token(client)
            resp = await client.get(
                f"{REDDIT_API_BASE}/r/bangalore/search",
                headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
                params={"q": query, "restrict_sr": "1", "sort": "relevance", "t": "year", "limit": 15},
            )
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])
            if not posts:
                return {"source": "Reddit", "status": "error", "data": "", "error": "No results"}

            lines = []
            for post in posts[:8]:
                d = post.get("data", {})
                title = (d.get("title") or "").strip()
                body = (d.get("selftext") or "").strip()[:200]
                lines.append(f"- {title} (score {d.get('score', 0)}) {body}".strip())
            return {"source": "Reddit", "status": "ok", "data": "\n".join(lines)}
    except Exception as e:
        return {"source": "Reddit", "status": "error", "data": "", "error": str(e)}


# ── Hacker News ──────────────────────────────────────────────────────────────

async def fetch_hackernews(locality: str) -> dict:
    """Algolia's public HN Search API — no key, no auth, no rate-limit signup."""
    query = f"Bangalore {locality} rent"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": "story", "hitsPerPage": 10},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if not hits:
                return {"source": "Hacker News", "status": "error", "data": "", "error": "No results"}

            lines = [
                f"- {(h.get('title') or '').strip()} ({h.get('points', 0)} points, {h.get('num_comments', 0)} comments)"
                for h in hits[:8]
            ]
            return {"source": "Hacker News", "status": "ok", "data": "\n".join(lines)}
    except Exception as e:
        return {"source": "Hacker News", "status": "error", "data": "", "error": str(e)}


# ── Google News ──────────────────────────────────────────────────────────────

async def fetch_google_news(locality: str) -> dict:
    """Google News RSS search feed — no key, no auth."""
    query = f"{locality} Bangalore rent property"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")[:8]
            if not items:
                return {"source": "Google News", "status": "error", "data": "", "error": "No results"}

            lines = [f"- {(item.findtext('title') or '').strip()}" for item in items]
            return {"source": "Google News", "status": "ok", "data": "\n".join(lines)}
    except ET.ParseError as e:
        return {"source": "Google News", "status": "error", "data": "", "error": f"Bad RSS response: {e}"}
    except Exception as e:
        return {"source": "Google News", "status": "error", "data": "", "error": str(e)}
