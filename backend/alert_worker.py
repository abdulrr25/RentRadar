"""
Saved-search matching worker.

Deliberately does NOT go through agent.py's LLM synthesis — alerts only need
"is there a new listing under budget", not a narrative brief, so this calls
the portal scrapers directly and skips the Groq call entirely. That keeps
alert runs cheap (Anakin search credits only, no LLM tokens) since this is
meant to run unattended on a schedule across every saved search.

Triggered by POST /internal/run-alerts (see main.py), called once daily by
the "Run saved-search alerts" GitHub Actions workflow — nothing here runs
on its own timer.
"""

import asyncio
import hashlib
import logging

import alerts_store
import briefs_store
from prompts import extract_price_int
from tools.scraper import fetch_nobroker, fetch_olx, fetch_housing
from channels.telegram import send_telegram
from channels.webpush import send_webpush
from channels.email import send_email

logger = logging.getLogger("rentradar.alerts")

# webpush is dispatched separately in run_all_alerts (below) — it has a
# three-way "gone" result that needs to deactivate the saved search, unlike
# telegram/email's plain success/fail.
_SENDERS = {
    "telegram": lambda target, message: send_telegram(target, message),
    "email": lambda target, message: send_email(target, "RentRadar: new match found", message),
}


async def _dispatch(channel: str, target: str, message: str) -> bool:
    sender = _SENDERS.get(channel)
    if sender is None:
        logger.error("Unknown alert channel: %s", channel)
        return False
    return await sender(target, message)


def _ref_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


async def _find_matches(locality: str, bhk: str, max_rent: int) -> list[dict]:
    """Fetch all three portals and return listings with a known price at/under budget."""
    results = await asyncio.gather(
        fetch_nobroker(locality, bhk, max_rent),
        fetch_olx(locality, bhk, max_rent),
        fetch_housing(locality, bhk, max_rent),
        return_exceptions=True,
    )

    matches = []
    for r in results:
        if isinstance(r, Exception) or r.get("status") != "ok":
            continue
        for item in r.get("results", []):
            price = extract_price_int(item.get("snippet", ""))
            if price is not None and price <= max_rent and item.get("url"):
                matches.append({
                    "source": r["source"],
                    "url": item["url"],
                    "title": item.get("title", ""),
                    "price": price,
                })
    return matches


async def run_all_alerts() -> dict:
    """Check every active, confirmed saved search for new matches. Returns a summary dict."""
    searches = await alerts_store.list_active_confirmed()
    sent = 0
    checked = 0
    errors = 0

    for s in searches:
        checked += 1
        if not s.get("target"):
            # Shouldn't happen — list_active_confirmed() only returns confirmed
            # rows, and confirmation always sets target — but never crash the
            # whole run over one bad row.
            errors += 1
            logger.error("Confirmed saved_search_id=%s has no target — skipping", s["id"])
            continue
        try:
            matches = await _find_matches(s["locality"], s["bhk"], s["max_rent"])
            for m in matches:
                ref = _ref_hash(m["url"])
                if await alerts_store.has_seen(s["id"], ref):
                    continue
                message = (
                    f"New {s['bhk']} match in {s['locality']} — "
                    f"₹{m['price']:,}/mo on {m['source']}. {m['url']}"
                )

                if s["channel"] == "webpush":
                    result = await send_webpush(s["target"], message)
                    if result == "gone":
                        # Browser subscription expired — it can never succeed
                        # again, so deactivate now rather than retrying this
                        # (and every other match) forever on every future run.
                        await alerts_store.deactivate(s["id"])
                        logger.info(
                            "Deactivated saved_search_id=%s — push subscription is gone", s["id"]
                        )
                        break
                    delivered = result == "sent"
                else:
                    delivered = await _dispatch(s["channel"], s["target"], message)

                if delivered:
                    sent += 1
                    await alerts_store.mark_seen(s["id"], ref)
                # else: leave unmarked so a transient send failure is retried
                # next run instead of being silently and permanently dropped.
            await alerts_store.mark_checked(s["id"])
        except Exception:
            errors += 1
            logger.exception("Alert check failed for saved_search_id=%s", s["id"])

    # Storage cleanup piggybacks on the daily run rather than needing its own
    # schedule. Never let a cleanup failure fail the alert run itself — the
    # notifications are the point, this is housekeeping.
    purged_seen = purged_briefs = purged_unconfirmed = 0
    try:
        purged_seen = await alerts_store.purge_seen_listings()
        purged_unconfirmed = await alerts_store.purge_unconfirmed()
        purged_briefs = await briefs_store.purge_expired()
    except Exception:
        logger.exception("Storage cleanup failed (alerts themselves were unaffected)")

    return {
        "checked": checked,
        "alerts_sent": sent,
        "errors": errors,
        "purged_seen_listings": purged_seen,
        "purged_unconfirmed": purged_unconfirmed,
        "purged_briefs": purged_briefs,
    }
