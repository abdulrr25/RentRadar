"""
Web Push (VAPID) — the only alert channel that needs zero external account.
No BSP, no bot, no email provider signup: VAPID is a self-generated keypair,
and delivery goes straight to the browser vendor's own push service
(Chrome -> FCM, Firefox -> Mozilla's push service, etc.) with no
intermediary to approve or bill you.

Requires VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, and VAPID_SUBJECT (a mailto:
or https: contact URL required by the spec) — generate a keypair once with:

    python -m backend.channels.webpush

and put the private key server-side (VAPID_PRIVATE_KEY) and the public key
in the frontend's NEXT_PUBLIC_VAPID_PUBLIC_KEY (it's not a secret — it's
handed to the browser to encrypt the subscription against).
"""

import asyncio
import json
import logging
import os

from pywebpush import webpush, WebPushException

logger = logging.getLogger("rentradar.webpush")


def _vapid_claims() -> dict:
    return {"sub": os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")}


async def send_webpush(subscription_json: str, message: str) -> bool:
    """
    Send a Web Push notification. `subscription_json` is the JSON-serialised
    PushSubscription object captured from the browser (endpoint + keys).
    Returns False (and marks the caller should deactivate) if the push
    service reports the subscription as gone (410/404) — browser
    subscriptions expire and can't be retried.
    """
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    if not private_key:
        logger.info("[WEBPUSH STUB — no VAPID_PRIVATE_KEY set] message=%r", message)
        return True

    try:
        subscription_info = json.loads(subscription_json)
    except (json.JSONDecodeError, TypeError):
        logger.error("Malformed push subscription JSON — cannot send")
        return False

    def _send():
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": "RentRadar", "body": message}),
            vapid_private_key=private_key,
            vapid_claims=_vapid_claims(),
        )

    try:
        await asyncio.to_thread(_send)
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            logger.info("Push subscription expired/gone — should be deactivated")
        else:
            logger.exception("Web push send failed")
        return False
    except Exception:
        # A malformed subscription (bad base64 in p256dh/auth, missing
        # fields) raises from inside pywebpush's own parsing, not as a
        # WebPushException — never let a bad client payload crash the caller.
        logger.exception("Web push send failed with an unexpected error")
        return False


def _generate_and_print_vapid_keys() -> None:
    """Run as `python -m channels.webpush` to generate a keypair for .env."""
    import base64
    from py_vapid import Vapid02
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    vapid = Vapid02()
    vapid.generate_keys()

    # Raw base64url-encoded values — single line, no PEM escaping needed.
    # Vapid.from_string() (used internally by pywebpush) accepts this form.
    raw_private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    private_b64url = base64.urlsafe_b64encode(raw_private).decode().rstrip("=")
    print("VAPID_PRIVATE_KEY=" + private_b64url)

    raw_public = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    public_b64url = base64.urlsafe_b64encode(raw_public).decode().rstrip("=")
    print("VAPID_PUBLIC_KEY=" + public_b64url)
    print("NEXT_PUBLIC_VAPID_PUBLIC_KEY=" + public_b64url + "  (same value, frontend env)")


if __name__ == "__main__":
    _generate_and_print_vapid_keys()
