"""
Property listing fetcher — uses a self-hosted SearXNG instance (see
../../searxng/) to find real listings from NoBroker, OLX, Housing.com,
99acres, and MagicBricks.

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


# Two portals have a well-defined genuine-single-listing URL shape, and
# ONLY that shape is a real listing — every other path on the domain is a
# locality/city/project browse page. For these, an allowlist (keep only the
# genuine shape) is far more robust than trying to blocklist every browse
# variant. Verified against a live corpus of ~380 URLs/portal across 8
# localities:
#   housing.com genuine: /rent/19960137-750-sqft-1-bhk-apartment-on-rent-in-...
#                        (a numeric listing id right after /rent/). Browse
#                        pages are /in/buy/..., /<area>-overview-P..., /flatmates/...,
#                        and /rent-<building>-...-rpid-AG... (a whole project).
#   olx.in genuine:      /item/...  (a single classified ad; the slug may be
#                        /item/for-rent-houses-apartments-c1723-2-bhk-... or
#                        /item/<slug>-iid-<id>, optionally under an /en-in/
#                        locale prefix). EVERYTHING else is a browse page:
#                        bare geo /<area>_g<id>, category /..._c<id>,
#                        query /q-..., and filtered /..._c<id>?filter=... .
#                        A pure blocklist missed the bare _g pages and the
#                        _c<id>?filter= variants (the "?" defeated a
#                        trailing /|$ anchor) and the pg-guest-houses pages.
#   nobroker.in genuine: /property/2-bhk-apartment-for-rent-in-<place>-for-rs-<n>
#                        (an individual property, always under /property/).
#                        Browse pages sit at the ROOT — /2bhk-flats-for-rent-in-<place>,
#                        /2-bhk-house-for-rent-in-<place> (any home type, not
#                        just "flats"), /2bhk-flats-for-rent-in-<project>-prjtl,
#                        /2bhk-flats-for-sale-in-<place> — and the in-site
#                        search is /property/rent/bangalore/<area>?searchParam=... .
#                        So genuine = under /property/ but NOT /property/rent/.
#                        (?!rent/) excludes that search path; nothing else
#                        genuine lives under /property/rent/.
#   99acres.com genuine: /detail/<numeric-id>-... (individual listing).
#                        Browse pages are /<area>-property-for-rent-...,
#                        /bangalore-real-estate-... etc.
#   magicbricks.com genuine: /propertyDetails/<id> or /property-for-rent/.../<id>.html
#                        Browse pages are /property-for-rent/bangalore-...
_GENUINE_LISTING_RE = {
    "housing.com": re.compile(r"/rent/\d+-", re.IGNORECASE),
    "olx.in": re.compile(r"/item/", re.IGNORECASE),
    "nobroker.in": re.compile(r"/property/(?!rent/)", re.IGNORECASE),
    "99acres.com": re.compile(r"/detail/\d+", re.IGNORECASE),
    "magicbricks.com": re.compile(
        r"(/propertyDetails/\d+|/property-for-rent/.+/\d+\.html)", re.IGNORECASE
    ),
}

# TITLE heuristics are a defensive fallback for any domain that has no URL
# allowlist above (none of our three portals today — they're all covered —
# but kept so an added source degrades safely instead of trusting every
# result). A locality/city results page titles itself "<N> BHK Flats for
# Rent in <Place>" with no specifics, often with the portal's own count
# ("197+" = 197 listings on one page). A genuine single listing names
# something specific (sqft, building, a price) so it won't match. The price
# guard keeps the greedy place-matcher from swallowing a genuine listing
# whose own title quotes a rent ("... for Rs 6,000").
_GENERIC_TITLE_RE = re.compile(
    r"(?:\d*\s*bhk\s+)?(?:flats?|houses?|apartments?|properties)\s+for\s+(?:rent|sale)\s+(?:in|near)\s+"
    r"[\w\s,.]+?(?:[-–]\s*[\w.]+)?\s*\d*\+?\s*$",
    re.IGNORECASE,
)
_LISTING_COUNT_RE = re.compile(r"\b\d{2,}\+")
_PRICE_IN_TITLE_RE = re.compile(r"(?:₹|\brs\.?)\s*\d", re.IGNORECASE)


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

    # Allowlist portals (all three today): the genuine-listing URL shape is
    # REQUIRED and authoritative. If the URL is that shape, trust it outright
    # (don't second-guess with the title heuristics); if it isn't, it's a
    # browse page.
    allow = _GENUINE_LISTING_RE.get(expected_domain)
    if allow is not None:
        return allow.search(low_url) is None

    # Fallback for any domain without an allowlist (defensive — see above).
    # Secondary title signals, skipped when the title quotes a specific
    # price, which marks a specific listing, not a bare results page.
    title = title.strip()
    if _PRICE_IN_TITLE_RE.search(title):
        return False
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


async def fetch_99acres(locality: str, bhk: str, max_rent: int) -> dict:
    """Search 99acres for rental listings — good public indexing of individual listings."""
    prompt = f'{bhk} flat for rent in {locality} Bangalore site:99acres.com'
    return await _search(prompt, "99acres", "99acres.com")


async def fetch_magicbricks(locality: str, bhk: str, max_rent: int) -> dict:
    """Search MagicBricks for rental listings — well indexed by search engines."""
    prompt = f'{bhk} apartment for rent {locality} Bangalore site:magicbricks.com'
    return await _search(prompt, "MagicBricks", "magicbricks.com")
