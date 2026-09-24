"""
Area-sentiment fetchers — Hacker News, Google News.

These used to go through Anakin's Wire API (see git history: holocron.py),
which billed per call same as the listing search. Neither actually needs a
paid intermediary:
  - Hacker News:  Algolia's public HN Search API (no key, no auth)
  - Google News:  public RSS search feed (no key, no auth)

Reddit was dropped from this list (not added here) — its official API
requires accepting Data API Terms that gate commercial use behind explicit
written approval, which isn't a fit for a product that may monetize later.
"""

import logging
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger("rentradar.sentiment_sources")

USER_AGENT = "RentRadar/1.0 (Bangalore rental search tool)"


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
