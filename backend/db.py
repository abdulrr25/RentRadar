"""
libSQL-backed storage for saved-search alerts and shareable briefs.

Was plain aiosqlite against a local file — but that file lived on Render's
default disk, which is wiped on every redeploy (Render's persistent disks
require a paid instance plan, which this project isn't on). Moved to
libsql_client instead: it speaks the same SQL dialect and the same client
API shape (execute/rows/batch), but can point at either a local file
(dev/tests, zero setup) or a hosted Turso database (production — free
tier, no expiry, no plan upgrade needed). alerts_store.py and
briefs_store.py needed only mechanical changes (result.rows instead of a
separate fetchone() cursor call, no manual commit — each statement
auto-commits), not a rewrite of their SQL.
"""

import os
from pathlib import Path

import libsql_client

DATABASE_URL = os.getenv("DATABASE_URL", f"file:{Path(__file__).parent / 'alerts.db'}")
DATABASE_AUTH_TOKEN = os.getenv("DATABASE_AUTH_TOKEN")

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_searches (
    id              TEXT PRIMARY KEY,
    channel         TEXT NOT NULL,
    target          TEXT,
    confirm_token   TEXT,
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
CREATE TABLE IF NOT EXISTS briefs (
    id         TEXT PRIMARY KEY,
    locality   TEXT NOT NULL,
    bhk        TEXT NOT NULL,
    max_rent   INTEGER NOT NULL,
    brief_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_briefs_created_at ON briefs(created_at);
"""

_client: libsql_client.Client | None = None


async def init_db() -> None:
    global _client
    kwargs = {"auth_token": DATABASE_AUTH_TOKEN} if DATABASE_AUTH_TOKEN else {}
    _client = libsql_client.create_client(DATABASE_URL, **kwargs)
    statements = [s.strip() for s in SCHEMA.split(";") if s.strip()]
    await _client.batch(statements)


async def close_db() -> None:
    if _client is not None:
        await _client.close()


def get_conn() -> libsql_client.Client:
    if _client is None:
        raise RuntimeError("Database not initialised — call init_db() at startup")
    return _client
