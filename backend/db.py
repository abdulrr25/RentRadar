"""
SQLite storage for saved-search alerts.

Deliberately not Postgres: zero infra to provision while the feature is
pre-launch. aiosqlite gives us real transactional updates (unlike the
append-only feedback.jsonl pattern), which saved_searches needs for
confirm/deactivate/last_checked_at. If usage grows past a single instance,
swap this module for a Postgres pool — alerts_store.py is the only caller,
so the migration surface is small.
"""

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "alerts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_searches (
    id              TEXT PRIMARY KEY,
    channel         TEXT NOT NULL,  -- 'telegram' | 'webpush' | 'email'
    target          TEXT,           -- telegram chat id / JSON push subscription / email address.
                                     -- NULL for telegram until the /start webhook confirms it.
    confirm_token   TEXT,           -- one-time token: the /start payload for telegram,
                                     -- the confirm-link token for email. NULL for webpush
                                     -- (browser permission grant IS the confirmation) and
                                     -- cleared once a channel confirms.
    locality        TEXT NOT NULL,
    bhk             TEXT NOT NULL,
    max_rent        INTEGER NOT NULL,
    confirmed       INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      INTEGER NOT NULL,
    last_checked_at INTEGER
);

CREATE TABLE IF NOT EXISTS seen_listings (
    saved_search_id TEXT NOT NULL REFERENCES saved_searches(id) ON DELETE CASCADE,
    ref_hash        TEXT NOT NULL,
    first_seen_at   INTEGER NOT NULL,
    PRIMARY KEY (saved_search_id, ref_hash)
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_confirm_token ON saved_searches(confirm_token);
"""

_conn: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _conn
    _conn = await aiosqlite.connect(DB_PATH)
    await _conn.execute("PRAGMA journal_mode=WAL;")
    await _conn.executescript(SCHEMA)
    await _conn.commit()


async def close_db() -> None:
    if _conn is not None:
        await _conn.close()


def get_conn() -> aiosqlite.Connection:
    if _conn is None:
        raise RuntimeError("Database not initialised — call init_db() at startup")
    return _conn
