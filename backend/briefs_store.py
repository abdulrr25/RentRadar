"""
Persistence for shareable search briefs.

Each successful search gets stored under a short URL-safe id so the result
can be opened later at /s/{id} and forwarded around (WhatsApp groups etc.).
Briefs expire after BRIEF_TTL_DAYS — the listings inside go stale quickly,
so there is no value in keeping them forever; cleanup happens inline on
each save, which keeps us free of any scheduled job.
"""

import secrets
import time

from db import get_conn

BRIEF_TTL_DAYS = 30
_TTL_SECONDS = BRIEF_TTL_DAYS * 24 * 3600


async def save_brief(locality: str, bhk: str, max_rent: int, brief_json: str) -> str:
    brief_id = secrets.token_urlsafe(6)  # 8 chars, ~2^48 space — ample for share links
    now = int(time.time())
    conn = get_conn()
    await conn.execute(
        """INSERT INTO briefs (id, locality, bhk, max_rent, brief_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (brief_id, locality, bhk, max_rent, brief_json, now),
    )
    # Inline TTL sweep — cheap (indexed on created_at) and avoids a cron.
    await conn.execute("DELETE FROM briefs WHERE created_at < ?", (now - _TTL_SECONDS,))
    await conn.commit()
    return brief_id


async def get_brief(brief_id: str) -> dict | None:
    conn = get_conn()
    cursor = await conn.execute(
        """SELECT locality, bhk, max_rent, brief_json, created_at
           FROM briefs WHERE id = ? AND created_at >= ?""",
        (brief_id, int(time.time()) - _TTL_SECONDS),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "locality": row[0],
        "bhk": row[1],
        "max_rent": row[2],
        "brief": row[3],
        "created_at": row[4],
    }
