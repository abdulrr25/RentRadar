"""
RentRadar FastAPI server.

POST /search                  — accepts a natural language query, streams SSE events back.
POST /feedback                 — accepts a user feedback rating + optional comment.
POST /alerts                   — create a saved search on one of three channels
                                  (telegram / webpush / email); each has its own opt-in flow.
POST /alerts/telegram/webhook   — inbound Telegram update; a "/start <token>" confirms.
GET  /alerts/confirm/{token}    — email confirmation link target.
DELETE /alerts/{id}             — deactivate a saved search.
POST /internal/run-alerts       — check all saved searches for new matches (scheduler-triggered).
GET  /health                    — liveness check; validates required env vars are present.
"""

import json
import asyncio
import os
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load .env from backend dir first, then fall back to project root
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

from parser import parse_query
from agent import agent
import db
import alerts_store
import briefs_store
from alert_worker import run_all_alerts
from channels.telegram import send_telegram, bot_start_link
from channels.webpush import send_webpush
from channels.email import send_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("rentradar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield
    await db.close_db()


# Docs disabled — this API is only ever called by RentRadar's own frontend,
# not consumed by third parties, so a public schema is pure recon for an
# attacker (it would otherwise list /internal/run-alerts and every field name).
app = FastAPI(
    title="RentRadar API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Rate limiting — in-memory (single-instance deployment; move to a Redis
# backend via slowapi's storage_uri if this ever scales past one instance).
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: local dev + this project's own Vercel deployments only.
# A blanket "*.vercel.app" or "*.onrender.com" regex would let ANY app on
# those platforms — not just this one — make credentialed cross-origin
# requests here. Add exact production domains via EXTRA_ORIGINS.
_extra = [o.strip() for o in os.getenv("EXTRA_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *_extra],
    allow_origin_regex=r"https://rentradar(-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    return {"service": "RentRadar API", "status": "ok"}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


@app.post("/search")
@limiter.limit("10/10minutes")
async def search(request: Request, body: SearchRequest):
    """
    Main search endpoint. Returns an SSE stream.

    Event types emitted:
      parsed          — structured query params
      fetching        — list of sources being fetched
      source_complete — per-source status as each finishes
      brief           — final synthesized JSON string
      share           — {id} of the persisted brief, for building a share link
      done            — stream end signal
      error           — pipeline error message (no internal details exposed)
    """

    async def stream():
        try:
            # Phase 1: parse
            parsed = parse_query(body.query)
            yield f"data: {json.dumps({'type': 'parsed', 'data': parsed})}\n\n"
            await asyncio.sleep(0)  # flush to client immediately

            # Phase 2: signal fetch start
            sources = [
                "Reddit", "Google News", "Hacker News",
                "NoBroker", "OLX", "Housing.com",
            ]
            yield f"data: {json.dumps({'type': 'fetching', 'sources': sources})}\n\n"
            await asyncio.sleep(0)

            # Phase 3: run agent (parallel fetch + LLM synthesis)
            result = await agent.ainvoke({
                "query": parsed,
                "raw_data": [],
                "brief": "",
                "error": "",
            })

            # Phase 4: emit per-source completion status
            for item in result["raw_data"]:
                yield f"data: {json.dumps({'type': 'source_complete', 'source': item['source'], 'status': item['status']})}\n\n"
                await asyncio.sleep(0.04)

            # Phase 5: final brief
            yield f"data: {json.dumps({'type': 'brief', 'data': result['brief']})}\n\n"
            await asyncio.sleep(0)

            # Phase 6: persist for sharing — skipped for error/unavailable
            # briefs, which aren't worth a share link. Best-effort: a storage
            # failure never breaks the search the user is looking at.
            try:
                brief_obj = json.loads(result["brief"])
                if not brief_obj.get("sources_unavailable") and not brief_obj.get("error"):
                    share_id = await briefs_store.save_brief(
                        parsed["locality"], parsed["bhk"], parsed["max_rent"], result["brief"]
                    )
                    yield f"data: {json.dumps({'type': 'share', 'id': share_id})}\n\n"
            except Exception:
                logger.exception("Failed to persist shareable brief")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            # Log full traceback server-side; send only a safe message to client
            logger.exception("Pipeline error for query: %s", body.query)
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while processing your request. Please try again.'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/brief/{brief_id}")
@limiter.limit("120/minute")
async def get_shared_brief(request: Request, brief_id: str):
    """
    Fetch a persisted brief for the /s/{id} share page. Generous rate limit:
    these requests arrive server-side from the Next.js host's small set of
    egress IPs, so a strict per-IP cap would throttle all share viewers
    collectively, not per-person.
    """
    if len(brief_id) > 32:
        raise HTTPException(status_code=404, detail="Not found")
    record = await briefs_store.get_brief(brief_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@app.get("/health")
async def health():
    missing = [k for k in ("ANAKIN_API_KEY", "GROQ_API_KEY") if not os.getenv(k)]
    if missing:
        return {"status": "degraded", "missing_env": missing}
    return {"status": "ok", "service": "RentRadar"}


FEEDBACK_FILE = Path(__file__).parent / "feedback.jsonl"


class FeedbackRequest(BaseModel):
    rating: str = Field(pattern="^(up|down)$")
    message: str = Field(default="", max_length=1000)
    query: str = Field(default="", max_length=300)


@app.post("/feedback")
@limiter.limit("20/hour")
async def feedback(request: Request, body: FeedbackRequest):
    """Append feedback as a JSON line. Best-effort — never blocks the UI on failure."""
    entry = {
        "ts": int(time.time()),
        "rating": body.rating,
        "message": body.message.strip(),
        "query": body.query.strip(),
    }
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Failed to persist feedback")
        return {"status": "error"}
    return {"status": "ok"}


# ── Saved-search alerts ──────────────────────────────────────────────────────
#
# Three channels, none needing a WhatsApp Business API account:
#   telegram — live once TELEGRAM_BOT_TOKEN/TELEGRAM_BOT_USERNAME are set
#              (free, no business verification — see channels/telegram.py)
#   webpush  — live as soon as a VAPID keypair exists (self-generated, no
#              external account at all — see channels/webpush.py)
#   email    — live once RESEND_API_KEY is set (see channels/email.py)
# Any channel without its env vars set falls back to a logging stub, so the
# whole pipeline is testable end-to-end regardless of which are configured.

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AlertRequest(BaseModel):
    channel: Literal["telegram", "webpush", "email"]
    target: str | None = Field(default=None, max_length=2000)
    locality: str = Field(min_length=1, max_length=100)
    bhk: str = Field(min_length=1, max_length=20)
    max_rent: int = Field(gt=0, le=10_000_000)

    @model_validator(mode="after")
    def _validate_target_for_channel(self):
        if self.channel == "email":
            if not self.target or not EMAIL_RE.match(self.target.strip()):
                raise ValueError("A valid email address is required for the email channel")
        elif self.channel == "webpush":
            if not self.target:
                raise ValueError("A push subscription is required for the webpush channel")
            try:
                sub = json.loads(self.target)
            except json.JSONDecodeError:
                raise ValueError("target must be a JSON-encoded push subscription")
            if not isinstance(sub, dict) or "endpoint" not in sub or "keys" not in sub:
                raise ValueError("target is not a valid push subscription")
        # telegram: target is intentionally absent at creation — filled in by the
        # /start webhook once the user actually opens the bot.
        return self


@app.post("/alerts")
@limiter.limit("5/hour")
async def create_alert(request: Request, body: AlertRequest):
    locality, bhk = body.locality.strip(), body.bhk.strip()

    if body.channel == "webpush":
        search_id = await alerts_store.create_pending(
            "webpush", body.target, None, locality, bhk, body.max_rent
        )
        await alerts_store.confirm_by_id(search_id)  # browser permission grant IS the opt-in
        await send_webpush(body.target, f"Subscribed — we'll ping you about new {bhk} matches in {locality}.")
        return {"id": search_id, "status": "confirmed"}

    if body.channel == "email":
        confirm_token = secrets.token_urlsafe(24)
        search_id = await alerts_store.create_pending(
            "email", body.target.strip(), confirm_token, locality, bhk, body.max_rent
        )
        confirm_url = f"{str(request.base_url).rstrip('/')}/alerts/confirm/{confirm_token}"
        await send_email(
            body.target.strip(),
            "Confirm your RentRadar alert",
            f"Confirm alerts for {bhk} in {locality} under ₹{body.max_rent:,}/mo:\n\n{confirm_url}\n\n"
            "If you didn't request this, ignore this email.",
        )
        return {"id": search_id, "status": "pending_confirmation"}

    # telegram
    link_token = secrets.token_urlsafe(16)
    telegram_link = bot_start_link(link_token)
    if telegram_link is None:
        raise HTTPException(status_code=503, detail="Telegram channel not configured")
    search_id = await alerts_store.create_pending(
        "telegram", None, link_token, locality, bhk, body.max_rent
    )
    return {"id": search_id, "status": "pending_confirmation", "telegram_link": telegram_link}


class TelegramUpdate(BaseModel):
    # Only the fields we actually read — Telegram's Update payload has many
    # more, all ignored (pydantic drops unknown fields by default).
    message: dict | None = None


@app.post("/alerts/telegram/webhook")
@limiter.limit("60/minute")
async def telegram_webhook(
    request: Request,
    body: TelegramUpdate,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    """
    Inbound Telegram webhook. Point Telegram's setWebhook at this URL with
    secret_token=TELEGRAM_WEBHOOK_SECRET (Telegram then sends that value back
    in the X-Telegram-Bot-Api-Secret-Token header on every update — this is
    Telegram's own signature mechanism, not a placeholder like the old
    WhatsApp static-secret approach).

    Requires TELEGRAM_WEBHOOK_SECRET to be set — returns 503 if it isn't.
    """
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Telegram webhook not configured")
    if x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    message = body.message or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")

    if not text.startswith("/start ") or chat_id is None:
        return {"status": "ignored"}

    link_token = text[len("/start "):].strip()
    confirmed_id = await alerts_store.confirm_by_token(link_token, target=str(chat_id))
    if confirmed_id is None:
        await send_telegram(str(chat_id), "That link has expired or was already used.")
        return {"status": "no_pending_search"}

    await send_telegram(str(chat_id), "You're all set — we'll message you here when a new match appears.")
    return {"status": "confirmed", "id": confirmed_id}


@app.get("/alerts/confirm/{token}", response_class=HTMLResponse)
async def confirm_email_alert(token: str):
    """Landing page for the confirmation link sent to email subscribers."""
    confirmed_id = await alerts_store.confirm_by_token(token)
    if confirmed_id is None:
        message = "This confirmation link is invalid or has already been used."
    else:
        message = "You're all set — we'll email you when a new match appears."
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>RentRadar</title></head>
<body style="font-family:system-ui,sans-serif;text-align:center;padding:4rem 1rem;color:#0f172a;">
<h1>RentRadar</h1><p>{message}</p></body></html>"""


@app.delete("/alerts/{search_id}")
@limiter.limit("20/hour")
async def delete_alert(request: Request, search_id: str):
    ok = await alerts_store.deactivate(search_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"status": "deactivated"}


@app.post("/internal/run-alerts")
async def internal_run_alerts(x_internal_secret: str = Header(default="")):
    """
    Checks every active, confirmed saved search for new matches. Meant to be
    called by a scheduler (e.g. a Render Cron Job), not by the frontend.
    Requires ALERTS_INTERNAL_SECRET to be set — returns 503 if it isn't, so
    this can't accidentally run unprotected in production.
    """
    secret = os.getenv("ALERTS_INTERNAL_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Alerts worker not configured")
    if x_internal_secret != secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    summary = await run_all_alerts()
    return summary
