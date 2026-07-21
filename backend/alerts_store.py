"""
CRUD helpers over the saved_searches / seen_listings tables.
No ORM — matches the rest of the backend's style of plain queries.
"""

import time
import uuid

from db import get_conn


async def create_saved_search(phone: str, locality: str, bhk: str, max_rent: int) -> str:
    search_id = uuid.uuid4().hex
    conn = get_conn()
    await conn.execute(
        """INSERT INTO saved_searches (id, phone, locality, bhk, max_rent, confirmed, active, created_at)
           VALUES (?, ?, ?, ?, ?, 0, 1, ?)""",
        (search_id, phone, locality, bhk, max_rent, int(time.time())),
    )
    await conn.commit()
    return search_id


async def confirm_latest_for_phone(phone: str) -> str | None:
    """Confirm the most recently created unconfirmed, active search for this phone. Returns its id, or None."""
    conn = get_conn()
    cursor = await conn.execute(
        """SELECT id FROM saved_searches
           WHERE phone = ? AND confirmed = 0 AND active = 1
           ORDER BY created_at DESC LIMIT 1""",
        (phone,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    await conn.execute("UPDATE saved_searches SET confirmed = 1 WHERE id = ?", (row[0],))
    await conn.commit()
    return row[0]


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
        """SELECT id, phone, locality, bhk, max_rent FROM saved_searches
           WHERE confirmed = 1 AND active = 1"""
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "phone": r[1], "locality": r[2], "bhk": r[3], "max_rent": r[4]}
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
