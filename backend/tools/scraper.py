"""
Property listing fetcher — uses a self-hosted SearXNG instance (see
../../searxng/) to find real listings from NoBroker, OLX, and Housing.com.

Direct scraping of these portals is blocked by bot detection, so we use web
search instead. Each portal returns several distinct result pages, each with
its own URL + snippet (often containing real prices) — we return ALL of them
so the agent can build a diverse, multi-platform listing set and link each
listing to its specific page.

Previously this called Anakin's paid /v1/search API. SearXNG is a free,
open-source metasearch engine we run ourselves — no per-query cost, at the
tradeoff of occasionally getting rate-limited by whichever upstream engine
(Google/Bing/DuckDuckGo) it queries, since there's no paid proxy pool behind
it. See source_health.py for how that shows up if it happens.
"""

import logging
import re
import httpx
import os
from urllib.parse import urlparse

logger = logging.getLogger("rentradar.scraper")


def _search_url() -> str:
    """Read at call time — never captured at module import."""
    return f"{os.getenv('SEARXNG_URL', '').rstrip('/')}/search"


def _matches_domain(url: str, expected_domain: str) -> bool:
    """
    True only for the real domain or a genuine subdomain of it — plain
    substring containment would also match a lookalike like
    "evilnobroker.in" or "nobroker.in.scam.com", showing a phishing link
    under a trusted "NoBroker" badge.
    """
    try:
        netloc = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return netloc == expected_domain or netloc.endswith("." + expected_domain)


# Per-portal URL shape of a locality/city/project-wide results page, or a
# wrong-transaction-type page (a for-sale page surfacing in a rent search) —
# anything that is NOT one specific flat. Seen live:
#   nobroker.in/2bhk-flats-for-rent-in-bellandur_bangalore         whole-locality page, a
#                                                                   dozen+ different prices on it
#   nobroker.in/2bhk-flats-for-rent-in-adarsh-rosewood-...-prjtl   whole-project page ("197+" listings)
#   nobroker.in/2bhk-flats-for-sale-in-...                         for sale, not rent
#   nobroker.in/property/rent/bangalore/{area}?searchParam=...     re-runs a location filter
#   housing.com/in/buy/...                                         for sale, not rent
#   olx.in/real-estate_c3/q-2-bhk-flats                            category/query browse page
# A genuine Housing.com listing (captured live, see test_scraper.py) instead
# looks like /rent/19960137-750-sqft-1-bhk-apartment-on-rent-in-kadubeesanahalli-bengaluru
# — a numeric listing ID up front, not a bare "<bhk> flats for rent in
# <place>" template — so for housing.com the ID prefix is required rather
# than pattern-matching the bad shape.
_GENERIC_URL_PATTERNS = {
    # \b not a literal leading "-": NoBroker's "any BHK" variant of this same
    # page (.../flats-for-rent-in-bellandur_bangalore) has "flats" right at
    # the start of the path, with no "2bhk-" prefix before it to anchor on.
    "nobroker.in": re.compile(r"\bflats-for-(?:rent|sale)-(?:in|near)-|searchparam=", re.IGNORECASE),
    "housing.com": re.compile(r"/(?:in/)?buy/", re.IGNORECASE),
    "olx.in": re.compile(r"/q-|_c\d+(?:/|$)", re.IGNORECASE),
}
_HOUSING_LISTING_ID_RE = re.compile(r"/rent/\d+-", re.IGNORECASE)

# A result's TITLE is the other, portal-agnostic signal: every portal above
# templates its locality/city search-results page title as "<N> BHK Flats
# for Rent in <Place>" with no building name, owner, or price in it — often
# with the portal's own trailing count ("197+" = 197 listings on this one
# page). The BHK count is itself optional in this template (NoBroker's
# "any BHK" variant titles itself just "Flats for Rent in <Place>"). A real
# single listing's title names something specific (sqft, building, "owner",
# etc.), so it won't fully match this bare template either way.
_GENERIC_TITLE_RE = re.compile(
    r"(?:\d*\s*bhk\s+)?(?:flats?|houses?|apartments?|properties)\s+for\s+(?:rent|sale)\s+(?:in|near)\s+"
    r"[\w\s,.]+?(?:[-–]\s*[\w.]+)?\s*\d*\+?\s*$",
    re.IGNORECASE,
)
_LISTING_COUNT_RE = re.compile(r"\b\d{2,}\+")


def _is_generic_listing_page(url: str, title: str, expected_domain: str) -> bool:
    """
    True when a result is a locality/city/project-wide search page, or the
    wrong transaction type (a for-sale page surfacing in a rent search) —
    not one specific flat. Showing one of these as if it were "this
    listing" — a single plucked-out price and a direct link to a page that
    actually lists a dozen to hundreds of differently-priced units — is the
    "fake/half information" a user hits the moment the details on the page
    don't match what the brief described.
    """
    low_url = url.lower()
    pattern = _GENERIC_URL_PATTERNS.get(expected_domain)
    if pattern and pattern.search(low_url):
        return True
    if expected_domain == "housing.com" and not _HOUSING_LISTING_ID_RE.search(low_url):
        return True
    title = title.strip()
    if _GENERIC_TITLE_RE.fullmatch(title) or _LISTING_COUNT_RE.search(title):
        return True
    return False


async def _search(prompt: str, source_name: str, expected_domain: str, limit: int = 6) -> dict:
    """
    Run a SearXNG web search and return a list of structured results.

    The `site:` search restriction is a hint to the underlying search
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
            response = await client.get(
                _search_url(),
                params={"q": prompt, "format": "json"},
            )
            response.raise_for_status()
            data = response.json()
            all_results = [
                {
                    "title": (r.get("title") or "").strip(),
                    "url": r.get("url"),
                    "snippet": (r.get("content") or "").strip(),
                }
                for r in data.get("results", [])[:limit]
                if r.get("content") and r.get("url")
            ]

            on_domain = [r for r in all_results if _matches_domain(r["url"], expected_domain)]
            results = [
                r for r in on_domain
                if not _is_generic_listing_page(r["url"], r["title"], expected_domain)
            ]

            dropped_domain = len(all_results) - len(on_domain)
            dropped_generic = len(on_domain) - len(results)
            if dropped_domain or dropped_generic:
                logger.info(
                    "%s: dropped %d wrong-domain + %d generic-listing-page result(s) out of %d",
                    source_name, dropped_domain, dropped_generic, len(all_results),
                )

            if not results:
                return {"source": source_name, "status": "error", "results": [],
                        "error": "No results returned by search"}

            return {"source": source_name, "status": "ok", "results": results}
    except httpx.HTTPStatusError as e:
        return {"source": source_name, "status": "error", "results": [], "error": str(e)}
    except Exception as e:
        return {"source": source_name, "status": "error", "results": [], "error": str(e)}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Search NoBroker for real listings in this locality.

    NOTE: We intentionally do NOT include the budget in the query.
    Putting ₹{max_rent} in the search string means the search returns pages
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
