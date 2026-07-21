"""
Telegram Bot API — free, official, no business verification required.

Unlike WhatsApp, this can be fully live with just a bot token from
@BotFather (message @BotFather -> /newbot -> takes ~2 minutes, no GST,
no dedicated phone number). If TELEGRAM_BOT_TOKEN isn't set, falls back to
a logging stub so the rest of the pipeline is still testable.
"""

import logging
import os

import httpx

logger = logging.getLogger("rentradar.telegram")

API_BASE = "https://api.telegram.org"

TELEGRAM_LIVE = bool(os.getenv("TELEGRAM_BOT_TOKEN"))


def bot_start_link(confirm_token: str) -> str | None:
    """
    Returns the t.me deep link that opens the bot with /start <token>
    pre-filled, or None if TELEGRAM_BOT_USERNAME isn't configured.
    """
    username = os.getenv("TELEGRAM_BOT_USERNAME")
    if not username:
        return None
    return f"https://t.me/{username}?start={confirm_token}"


async def send_telegram(chat_id: str, message: str) -> bool:
    """Send a Telegram message. Returns True if sent (or logged, in stub mode)."""
    if not chat_id:
        logger.warning("Refusing to send — empty chat_id")
        return False

    if not TELEGRAM_LIVE:
        logger.info("[TELEGRAM STUB] to=%s message=%r", chat_id, message)
        return True

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.post(
                f"{API_BASE}/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
            )
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Telegram send failed for chat_id=%s", chat_id)
        return False
