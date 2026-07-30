"""
CRUD helpers over the saved_searches / seen_listings tables.
No ORM — matches the rest of the backend's style of plain queries.
"""

import time
import uuid

from db import get_conn

# How long a "we already told them about this listing" record is kept.
# It exists purely to suppress duplicate notifications, and rental listings
# go stale fast — if the same URL resurfaces after this long it's a fresh
# listing in practice, and notifying again is the right behaviour.
SEEN_TTL_DAYS = 90
_SEEN_TTL_SECONDS = SEEN_TTL_DAYS * 24 * 3600

# How long an unclicked confirmation link stays valid. Kept short on purpose:
# a confirm token is a bearer credential — anyone holding the link can attach
# a Telegram chat or activate an email subscription — so one that never
# expires is a standing liability in an old inbox or chat history.
UNCONFIRMED_TTL_HOURS = 48
_UNCONFIRMED_TTL_SECONDS = UNCONFIRMED_TTL_HOURS * 3600


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
    return search_id


async def confirm_by_id(search_id: str) -> bool:
    """Confirm a specific saved search (used for webpush, where opt-in is immediate)."""
    conn = get_conn()
    result = await conn.execute(
        "UPDATE saved_searches SET confirmed = 1, confirm_token = NULL WHERE id = ? AND active = 1",
        (search_id,),
    )
    return result.rows_affected > 0


async def confirm_by_token(confirm_token: str, target: str | None = None) -> str | None:
    """
    Confirm the saved search matching this token. If `target` is given (the
    telegram webhook case, where the chat id wasn't known at creation time),
    it's written in along with confirmation. Returns the search id, or None
    if no active, unconfirmed, unexpired row has this token.

    The age check lives here rather than relying on purge_unconfirmed() to
    have swept the row — expiry is a security property, so it must hold the
    moment the link is used, not merely by the next time a cleanup job runs.
    """
    conn = get_conn()
    cutoff = int(time.time()) - _UNCONFIRMED_TTL_SECONDS
    result = await conn.execute(
        """SELECT id FROM saved_searches
           WHERE confirm_token = ? AND confirmed = 0 AND active = 1
             AND created_at >= ?""",
        (confirm_token, cutoff),
    )
    if not result.rows:
        return None
    search_id = result.rows[0][0]
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
    return search_id


async def deactivate(search_id: str) -> bool:
    conn = get_conn()
    result = await conn.execute(
        "UPDATE saved_searches SET active = 0 WHERE id = ?", (search_id,)
    )
    return result.rows_affected > 0


async def list_active_confirmed() -> list[dict]:
    conn = get_conn()
    result = await conn.execute(
        """SELECT id, channel, target, locality, bhk, max_rent FROM saved_searches
           WHERE confirmed = 1 AND active = 1"""
    )
    return [
        {"id": r[0], "channel": r[1], "target": r[2], "locality": r[3], "bhk": r[4], "max_rent": r[5]}
        for r in result.rows
    ]


async def mark_checked(search_id: str) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE saved_searches SET last_checked_at = ? WHERE id = ?",
        (int(time.time()), search_id),
    )


async def has_seen(search_id: str, ref_hash: str) -> bool:
    conn = get_conn()
    result = await conn.execute(
        "SELECT 1 FROM seen_listings WHERE saved_search_id = ? AND ref_hash = ?",
        (search_id, ref_hash),
    )
    return len(result.rows) > 0


async def mark_seen(search_id: str, ref_hash: str) -> None:
    conn = get_conn()
    await conn.execute(
        """INSERT OR IGNORE INTO seen_listings (saved_search_id, ref_hash, first_seen_at)
           VALUES (?, ?, ?)""",
        (search_id, ref_hash, int(time.time())),
    )


async def purge_unconfirmed() -> int:
    """
    Delete signups whose confirmation link was never used and has now expired.

    Someone who starts a Telegram or email signup and never completes it
    leaves a confirmed=0 row behind. Nothing removed those, so they
    accumulated indefinitely — each still holding an (indexed) confirm_token.
    confirm_by_token() already refuses them once expired, so deleting them
    changes no behaviour; it just stops dead rows and stale bearer tokens
    from being retained forever.

    Returns the number of rows removed.
    """
    conn = get_conn()
    cutoff = int(time.time()) - _UNCONFIRMED_TTL_SECONDS
    result = await conn.execute(
        "DELETE FROM saved_searches WHERE confirmed = 0 AND created_at < ?",
        (cutoff,),
    )
    return result.rows_affected


async def purge_seen_listings() -> int:
    """
    Delete dedup rows that can no longer suppress a real notification.

    This table only ever got INSERTs — nothing deleted from it, ever. The
    ON DELETE CASCADE in the schema never fires either, because deactivate()
    flags a search inactive rather than deleting the row, so a cancelled
    subscription kept its entire dedup ledger forever.

    Two classes of dead row:
      - anything past SEEN_TTL_DAYS
      - everything belonging to an inactive search (there is no reactivate
        path, so those can never notify again)

    Returns the number of rows removed.
    """
    conn = get_conn()
    cutoff = int(time.time()) - _SEEN_TTL_SECONDS
    result = await conn.execute(
        """DELETE FROM seen_listings
           WHERE first_seen_at < ?
              OR saved_search_id IN (SELECT id FROM saved_searches WHERE active = 0)""",
        (cutoff,),
    )
    return result.rows_affected
