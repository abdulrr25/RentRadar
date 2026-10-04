"""
Community listings — real flats submitted directly by Telegram DM (see
main.py's /alerts/telegram/webhook), not scraped from a portal.

Unlike scraper.py's sources, these arrive already structured (parsed once
at submission time by parser.parse_query() — see community_store.py), so
there's no raw snippet to extract a price/locality from here. That's why
this returns a "listings" key instead of scraper.py's "results": it's a
deliberate shape difference so agent.py can tell "ready to use as-is" apart
from "needs the LLM to extract it" at a glance, and route each accordingly.
"""

import community_store

SOURCE_NAME = "Community"


async def fetch_community(
    locality: str, bhk: str, max_rent: int, min_rent: int | None = None
) -> dict:
    """
    Returns {source, status, listings:[{locality_detail, rent, bhk, source,
    highlights, url}]} — each entry already shaped to match ListingCards.tsx's
    Listing interface directly.

    status follows the same convention scraper.py already uses for its
    sources: "ok" only when something actually matched, "error" with a
    plain explanation when the query ran fine but found nothing — not a
    real failure, just "no submissions here yet" (expected and common,
    especially early on), but still the right signal for the UI pill and
    for agent.py to tell "nothing to add" apart from "found a listing".
    """
    rows = await community_store.search_listings(locality, bhk, max_rent, min_rent)
    listings = [
        {
            "locality_detail": f"{row['locality']} (community submission)",
            "rent": row["rent"],
            "bhk": row["bhk"],
            "source": SOURCE_NAME,
            "highlights": [row["description"][:120]],
            "url": None,
            # Recency is most of what makes a user trust a listing a
            # stranger typed in — the card shows this as "posted N days ago".
            "posted_at": row["created_at"],
        }
        for row in rows
    ]
    if not listings:
        return {"source": SOURCE_NAME, "status": "error", "listings": [],
                "error": "No community listings matched this search"}
    return {"source": SOURCE_NAME, "status": "ok", "listings": listings}
