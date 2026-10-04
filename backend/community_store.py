"""
CRUD helpers over the community_listings table.
No ORM — matches the rest of the backend's style of plain queries.

Listings come from a free-text Telegram DM parsed by parser.parse_query();
see main.py's /alerts/telegram/webhook for the submission flow and
tools/community.py for how these get pulled into a /search result.
"""

import time
import uuid

from db import get_conn

# Rentals go stale fast — same reasoning as the 90-day seen_listings TTL in
# alerts_store.py, just a much shorter window since this is the listing
# itself, not a dedup record.
EXPIRY_DAYS = 14
_EXPIRY_SECONDS = EXPIRY_DAYS * 24 * 3600

# Per chat_id, per rolling 24h — caps spam/abuse without needing an account
# system. Checked by the webhook handler before create_listing() is called.
SUBMIT_LIMIT_PER_DAY = 5
_SUBMIT_WINDOW_SECONDS = 24 * 3600


async def count_recent_by_chat(chat_id: str) -> int:
    conn = get_conn()
    cutoff = int(time.time()) - _SUBMIT_WINDOW_SECONDS
    result = await conn.execute(
        "SELECT count(*) FROM community_listings WHERE chat_id = ? AND created_at >= ?",
        (chat_id, cutoff),
    )
    return result.rows[0][0] if result.rows else 0


async def create_listing(chat_id: str, locality: str, bhk: str, rent: int, description: str) -> str:
    listing_id = uuid.uuid4().hex
    now = int(time.time())
    conn = get_conn()
    await conn.execute(
        """INSERT INTO community_listings
           (id, chat_id, locality, bhk, rent, description, status, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (listing_id, chat_id, locality, bhk, rent, description, now, now + _EXPIRY_SECONDS),
    )
    return listing_id


async def search_listings(
    locality: str, bhk: str, max_rent: int, min_rent: int | None = None
) -> list[dict]:
    """
    Active, unexpired, in-budget listings for an exact locality+bhk match —
    consistent with how fetch_nobroker/fetch_olx/fetch_housing each target
    one exact bhk rather than a range. Newest first, capped to a handful so
    one prolific submitter can't crowd out everything else.

    Unlike the scraped sources, rent here is always known (it's a required
    column), so both bounds can be applied in SQL rather than leaving
    unknown-price listings in for agent.py to keep.
    """
    conn = get_conn()
    now = int(time.time())
    sql = """SELECT id, locality, bhk, rent, description, created_at FROM community_listings
             WHERE locality = ? AND bhk = ? AND status = 'active'
               AND expires_at > ? AND rent <= ?"""
    params: list = [locality, bhk, now, max_rent]
    if min_rent is not None:
        sql += " AND rent >= ?"
        params.append(min_rent)
    sql += " ORDER BY created_at DESC LIMIT 10"

    result = await conn.execute(sql, tuple(params))
    return [
        {"id": r[0], "locality": r[1], "bhk": r[2], "rent": r[3],
         "description": r[4], "created_at": r[5]}
        for r in result.rows
    ]


async def purge_expired() -> int:
    """Delete rows past their expiry. Returns the number of rows removed."""
    conn = get_conn()
    result = await conn.execute(
        "DELETE FROM community_listings WHERE expires_at < ?",
        (int(time.time()),),
    )
    return result.rows_affected
