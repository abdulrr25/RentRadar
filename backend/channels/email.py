"""
Email via Resend — no GST/business verification needed, generous free tier.
Falls back to a logging stub if RESEND_API_KEY isn't set, same pattern as
the other channels.
"""

import logging
import os

import httpx

logger = logging.getLogger("rentradar.email")

RESEND_API_URL = "https://api.resend.com/emails"

EMAIL_LIVE = bool(os.getenv("RESEND_API_KEY"))

# Where operational alerts (e.g. Anakin credits exhausted) go — not a
# user-facing channel, just the site owner's inbox.
ADMIN_ALERT_EMAIL = os.getenv("ADMIN_ALERT_EMAIL", "abdulr6503@gmail.com")


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via Resend. Returns True if sent (or logged, in stub mode)."""
    if not to or "@" not in to:
        logger.warning("Refusing to send — invalid email address")
        return False

    if not EMAIL_LIVE:
        logger.info("[EMAIL STUB] to=%s subject=%r body=%r", to, subject, body)
        return True

    from_address = os.getenv("RESEND_FROM_EMAIL", "RentRadar <onboarding@resend.dev>")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_address,
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
            )
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Email send failed")
        return False


async def send_admin_alert(subject: str, body: str) -> bool:
    """Send an operational alert to the site admin, reusing the same
    stub-until-configured send_email path (logs instead of sending until
    RESEND_API_KEY is set)."""
    return await send_email(ADMIN_ALERT_EMAIL, subject, body)
