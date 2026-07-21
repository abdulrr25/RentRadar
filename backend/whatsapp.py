"""
WhatsApp sending — currently a logging stub.

No WhatsApp Business API account exists yet (AiSensy or otherwise). Every
call to send_whatsapp() below just logs what would have been sent, so the
rest of the alerts pipeline (signup, matching, dedup) can be built and
tested end-to-end today.

TO GO LIVE: once an AiSensy (or other BSP) account + approved templates
exist, replace the body of send_whatsapp() with a real HTTP call to their
send-template-message endpoint, using their actual request/auth shape from
their current API docs — this stub does not guess at that shape. Keep the
function signature the same so no caller needs to change.
"""

import logging
import os

logger = logging.getLogger("rentradar.whatsapp")

WHATSAPP_LIVE = bool(os.getenv("AISENSY_API_KEY"))


def _mask_phone(phone: str) -> str:
    """PII — never log a full phone number, even in stub mode."""
    p = phone.strip()
    return f"***{p[-4:]}" if len(p) >= 4 else "***"


async def send_whatsapp(phone: str, message: str) -> bool:
    """
    Send a WhatsApp message. Returns True if "sent" (stub: always True unless
    the phone number is obviously malformed).

    Stub mode (default): logs the message instead of calling any API.
    """
    if not phone or len(phone.strip()) < 8:
        logger.warning("Refusing to send — invalid phone: %r", _mask_phone(phone or ""))
        return False

    if not WHATSAPP_LIVE:
        logger.info("[WHATSAPP STUB] to=%s message=%r", _mask_phone(phone), message)
        return True

    # AISENSY_API_KEY is set but no real integration has been written yet —
    # fail loudly rather than silently pretending to send.
    logger.error(
        "AISENSY_API_KEY is set but send_whatsapp() has no real implementation "
        "wired up yet — see the module docstring."
    )
    return False
