"""
Detects whether an Anakin API failure looks like exhausted credits/quota,
as opposed to a generic network or server error — used to decide whether
to page the admin with a "recharge or rotate the key" alert.

Anakin doesn't document a stable error shape for this, so this is a best
effort match on the HTTP status and response body rather than a single
known error code.
"""

_CREDIT_KEYWORDS = ("credit", "insufficient", "quota", "balance", "payment required")


def is_credit_exhausted(status_code: int | None, body: str) -> bool:
    if status_code == 402:
        return True
    text = (body or "").lower()
    return any(keyword in text for keyword in _CREDIT_KEYWORDS)
