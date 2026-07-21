"""
CRUD helpers over the saved_searches / seen_listings tables.
No ORM — matches the rest of the backend's style of plain queries.
"""

import time
import uuid

from db import get_conn


async def create_pending(channel: str, target: str | None, confirm_token: str | None,
                          locality: str, bhk: str, max_rent: int) -> str:
    """
    Create a saved search awaiting confirmation.

    - webpush: target is the push subscription JSON, confirm_token is None —
      caller (main.py) confirms it immediately, since the browser permission
      grant already IS the opt-in.
    - email: target is the email address, confirm_token is the link token
      sent in the confirmation email.
    - telegram: target is None until the /start webhook fills it in;
      confirm_token is the /start payload used to match that webhook back
      to this row.
    """
    search_id = uuid.uuid4().hex
    conn = get_conn()
    await conn.execute(
        """INSERT INTO saved_searches
           (id, channel, target, confirm_token, locality, bhk, max_rent, confirmed, active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
        (search_id, channel, target, confirm_token, locality, bhk, max_rent, int(time.time())),
    )
    await conn.commit()
    return search_id


async def confirm_by_id(search_id: str) -> bool:
    """Confirm a specific saved search (used for webpush, where opt-in is immediate)."""
    conn = get_conn()
    cursor = await conn.execute(
        "UPDATE saved_searches SET confirmed = 1, confirm_token = NULL WHERE id = ? AND active = 1",
        (search_id,),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def confirm_by_token(confirm_token: str, target: str | None = None) -> str | None:
    """
    Confirm the saved search matching this token. If `target` is given (the
    telegram webhook case, where the chat id wasn't known at creation time),
    it's written in along with confirmation. Returns the search id, or None
    if no active, unconfirmed row has this token.
    """
    conn = get_conn()
    cursor = await conn.execute(
        """SELECT id FROM saved_searches
           WHERE confirm_token = ? AND confirmed = 0 AND active = 1""",
        (confirm_token,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    search_id = row[0]
    if target is not None:
        await conn.execute(
            "UPDATE saved_searches SET confirmed = 1, confirm_token = NULL, target = ? WHERE id = ?",
            (target, search_id),
        )
    else:
        await conn.execute(
            "UPDATE saved_searches SET confirmed = 1, confirm_token = NULL WHERE id = ?",
            (search_id,),
        )
    await conn.commit()
    return search_id


async def deactivate(search_id: str) -> bool:
    conn = get_conn()
    cursor = await conn.execute(
        "UPDATE saved_searches SET active = 0 WHERE id = ?", (search_id,)
    )
    await conn.commit()
    return cursor.rowcount > 0


async def list_active_confirmed() -> list[dict]:
    conn = get_conn()
    cursor = await conn.execute(
        """SELECT id, channel, target, locality, bhk, max_rent FROM saved_searches
           WHERE confirmed = 1 AND active = 1"""
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "channel": r[1], "target": r[2], "locality": r[3], "bhk": r[4], "max_rent": r[5]}
        for r in rows
    ]


async def mark_checked(search_id: str) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE saved_searches SET last_checked_at = ? WHERE id = ?",
        (int(time.time()), search_id),
    )
    await conn.commit()


async def has_seen(search_id: str, ref_hash: str) -> bool:
    conn = get_conn()
    cursor = await conn.execute(
        "SELECT 1 FROM seen_listings WHERE saved_search_id = ? AND ref_hash = ?",
        (search_id, ref_hash),
    )
    return await cursor.fetchone() is not None


async def mark_seen(search_id: str, ref_hash: str) -> None:
    conn = get_conn()
    await conn.execute(
        """INSERT OR IGNORE INTO seen_listings (saved_search_id, ref_hash, first_seen_at)
           VALUES (?, ?, ?)""",
        (search_id, ref_hash, int(time.time())),
    )
    await conn.commit()
