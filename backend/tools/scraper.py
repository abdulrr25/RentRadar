"""
Property listing fetcher — uses Anakin's /v1/search API to find real listings
from NoBroker, OLX, and Housing.com.

Direct scraping of these portals is blocked by bot detection, so we use web
search. Each portal returns several distinct result pages, each with its own
URL + snippet (often containing real prices) — we return ALL of them so the
agent can build a diverse, multi-platform listing set and link each listing to
its specific page.
"""

import logging
import httpx
import os
from urllib.parse import urlparse

from tools.anakin_errors import is_credit_exhausted

logger = logging.getLogger("rentradar.scraper")

SEARCH_URL = "https://api.anakin.io/v1/search"


def _headers() -> dict:
    return {
        "X-API-Key": os.getenv("ANAKIN_API_KEY", ""),
        "Content-Type": "application/json",
    }


def _matches_domain(url: str, expected_domain: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return expected_domain in netloc


def _is_generic_listing_page(url: str) -> bool:
    """
    True when a URL is a locality-wide search/category page, not one
    specific property — seen live: NoBroker returning
    ".../property/rent/bangalore/{area}?searchParam=<base64 location filter>"
    URLs. That page just re-runs a location filter and shows whatever is
    currently listed there; it's not "this listing", and showing it as if
    it were one specific flat is the "fake/half information" a user hits
    the exact moment the listing turns out not to be the flat described.
    """
    return "searchparam=" in url.lower()


async def _search(prompt: str, source_name: str, expected_domain: str, limit: int = 6) -> dict:
    """
    Run an Anakin web search and return a list of structured results.

    Anakin's `site:` search restriction is a hint to the underlying search
    engine, not a hard filter — in practice a meaningful share of results
    come back from other domains entirely (seen live: a "site:nobroker.in"
    search returning housing.com, 99acres.com, squareyards.com pages). Every
    result gets labeled with `source_name` regardless of where it actually
    came from — passing that straight through would show a "NoBroker" badge
    linking to a housing.com page, which is actively misleading, not just
    imprecise. So results are filtered to the expected domain here, before
    the caller ever sees them, rather than trusting the search query alone.

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
            all_results = [
                {
                    "title": (r.get("title") or "").strip(),
                    "url": r.get("url"),
                    "snippet": (r.get("snippet") or "").strip(),
                }
                for r in data.get("results", [])
                if r.get("snippet") and r.get("url")
            ]

            on_domain = [r for r in all_results if _matches_domain(r["url"], expected_domain)]
            results = [r for r in on_domain if not _is_generic_listing_page(r["url"])]

            dropped_domain = len(all_results) - len(on_domain)
            dropped_generic = len(on_domain) - len(results)
            if dropped_domain or dropped_generic:
                logger.info(
                    "%s: dropped %d wrong-domain + %d generic-listing-page result(s) out of %d",
                    source_name, dropped_domain, dropped_generic, len(all_results),
                )

            if not results:
                return {"source": source_name, "status": "error", "results": [],
                        "error": "No results returned by search API"}

            return {"source": source_name, "status": "ok", "results": results}
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response is not None else ""
        status = e.response.status_code if e.response is not None else None
        return {
            "source": source_name, "status": "error", "results": [], "error": str(e),
            "credit_exhausted": is_credit_exhausted(status, body),
        }
    except Exception as e:
        return {"source": source_name, "status": "error", "results": [], "error": str(e),
                "credit_exhausted": False}


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
    return await _search(prompt, "NoBroker", "nobroker.in")


async def fetch_olx(locality: str, bhk: str, max_rent: int) -> dict:
    """Search OLX for rental ads in this locality."""
    prompt = f'{bhk} for rent {locality} Bangalore site:olx.in'
    return await _search(prompt, "OLX", "olx.in")


async def fetch_housing(locality: str, bhk: str, max_rent: int) -> dict:
    """Search Housing.com for rental listings in this locality."""
    prompt = f'{bhk} rental flat {locality} Bangalore site:housing.com'
    return await _search(prompt, "Housing.com", "housing.com")
