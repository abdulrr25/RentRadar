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

Each item keeps its URL and publication date. Both APIs return them and
this module used to discard both, keeping only the headline text — which
made every downstream claim (scam alerts, red flags, price trend, locality
scores) impossible to cite or date. Measured consequences of that, before
this changed: HN stories from 2017 and 2023 surfaced as current
"tech-worker signal", and city-wide news about a corporate leasing fraud
was rendered as a scam alert for whichever locality the user searched. See
prompts.py (ref tagging) and agent.py (uncited claims are dropped).
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

logger = logging.getLogger("rentradar.sentiment_sources")

USER_AGENT = "RentRadar/1.0 (Bangalore rental search tool)"

# Anything older than this is dropped outright rather than shown with its
# date: a 2017 HN thread is not "what people are saying about this area",
# and presenting it as such is the kind of thing that makes the whole brief
# untrustworthy. Items inside the window are kept but always rendered with
# their date, so the reader can weigh a 5-month-old headline themselves.
MAX_AGE_DAYS = 365
_MAX_AGE_SECONDS = MAX_AGE_DAYS * 24 * 3600


def _rfc822_to_epoch(value: "str | None") -> "int | None":
    """Parse an RSS pubDate ('Wed, 27 May 2026 07:00:00 GMT') to epoch seconds."""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    # parsedate_to_datetime returns None for some malformed inputs on older
    # Pythons (rather than raising) — guard so .tzinfo can't AttributeError.
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _is_fresh(published_at: "int | None", now: int) -> bool:
    # Undated items are kept: the date is missing, not old, and dropping
    # them would quietly discard most of a source on a bad parse.
    return published_at is None or (now - published_at) <= _MAX_AGE_SECONDS


def _mentions(locality: str, title: str) -> bool:
    """
    Whether this headline is actually about the locality the user searched.

    A `site:`-free news search for "<locality> Bangalore rent" returns
    mostly city-wide stories — measured live: 1 of 8 results for Indiranagar
    actually mentioned Indiranagar. The LLM can't tell the difference from
    the text alone, so it's decided here and passed through as a marker.
    """
    return bool(locality) and locality.lower() in (title or "").lower()


def _finish(source: str, items: list, error: str) -> dict:
    """Shared return shape. Empty is reported as an error status, matching
    the convention scraper.py already uses for a search that ran fine but
    found nothing."""
    if not items:
        return {"source": source, "status": "error", "items": [], "error": error}
    items.sort(key=lambda i: i["published_at"] or 0, reverse=True)
    return {"source": source, "status": "ok", "items": items}


# ── Hacker News ──────────────────────────────────────────────────────────────

async def fetch_hackernews(locality: str) -> dict:
    """Algolia's public HN Search API — no key, no auth, no rate-limit signup."""
    query = f"Bangalore {locality} rent"
    now = int(datetime.now(timezone.utc).timestamp())
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": "story", "hitsPerPage": 10},
            )
            resp.raise_for_status()
            items = []
            for h in resp.json().get("hits", [])[:8]:
                title = (h.get("title") or "").strip()
                if not title:
                    continue
                # created_at_i is a ready-made unix timestamp — far more
                # robust than parsing the ISO "…Z" string, which needs
                # Python 3.11+ and this project pins no runtime version.
                raw_ts = h.get("created_at_i")
                published_at = int(raw_ts) if isinstance(raw_ts, (int, float)) else None
                if not _is_fresh(published_at, now):
                    continue
                items.append({
                    "title": title,
                    # The HN permalink, not the submitted article: it's the
                    # discussion that carries the signal we're quoting.
                    "url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "published_at": published_at,
                    "mentions_locality": _mentions(locality, title),
                    "points": h.get("points", 0),
                })
            return _finish("Hacker News", items, "No recent results")
    except Exception as e:
        return {"source": "Hacker News", "status": "error", "items": [], "error": str(e)}


# ── Google News ──────────────────────────────────────────────────────────────

async def fetch_google_news(locality: str) -> dict:
    """Google News RSS search feed — no key, no auth."""
    query = f"{locality} Bangalore rent property"
    now = int(datetime.now(timezone.utc).timestamp())
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = []
            for item in root.findall(".//item")[:8]:
                title = (item.findtext("title") or "").strip()
                if not title:
                    continue
                published_at = _rfc822_to_epoch(item.findtext("pubDate"))
                if not _is_fresh(published_at, now):
                    continue
                items.append({
                    "title": title,
                    "url": (item.findtext("link") or "").strip() or None,
                    "published_at": published_at,
                    "mentions_locality": _mentions(locality, title),
                })
            return _finish("Google News", items, "No recent results")
    except ET.ParseError as e:
        return {"source": "Google News", "status": "error", "items": [],
                "error": f"Bad RSS response: {e}"}
    except Exception as e:
        return {"source": "Google News", "status": "error", "items": [], "error": str(e)}
