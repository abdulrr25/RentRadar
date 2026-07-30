"""
Persistence for user feedback.

Was appended to a local feedback.jsonl file — but that file lives on Render's
default disk, which is wiped on every redeploy (same problem that moved
saved-search alerts to libSQL, see db.py). Every rating submitted between
two deploys was silently lost, which is worse than not collecting it at all:
the UI thanks the user and implies it was received.

Unlike briefs, feedback has NO TTL sweep — it's a small, slow-growing table
and its whole value is being able to look back over time at what people said.
"""

import time
import uuid

from db import get_conn


async def save_feedback(rating: str, message: str, query: str) -> str:
    feedback_id = uuid.uuid4().hex
    conn = get_conn()
    await conn.execute(
        """INSERT INTO feedback (id, rating, message, query, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (feedback_id, rating, message, query, int(time.time())),
    )
    return feedback_id


async def list_feedback(limit: int = 200) -> list[dict]:
    """Most recent first — for reading back what users have said."""
    conn = get_conn()
    result = await conn.execute(
        """SELECT id, rating, message, query, created_at FROM feedback
           ORDER BY created_at DESC LIMIT ?""",
        (limit,),
    )
    return [
        {"id": r[0], "rating": r[1], "message": r[2], "query": r[3], "created_at": r[4]}
        for r in result.rows
    ]


async def counts() -> dict:
    """Aggregate up/down tally."""
    conn = get_conn()
    result = await conn.execute("SELECT rating, count(*) FROM feedback GROUP BY rating")
    tally = {row[0]: row[1] for row in result.rows}
    return {"up": tally.get("up", 0), "down": tally.get("down", 0)}
