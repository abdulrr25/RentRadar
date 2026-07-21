"""
RentRadar FastAPI server.

POST /search              — accepts a natural language query, streams SSE events back.
POST /feedback             — accepts a user feedback rating + optional comment.
POST /alerts                — create a saved search (unconfirmed until WhatsApp reply).
POST /alerts/webhook        — inbound WhatsApp message webhook; "YES" confirms a saved search.
DELETE /alerts/{id}         — deactivate a saved search.
POST /internal/run-alerts   — check all saved searches for new matches (scheduler-triggered).
GET  /health                — liveness check; validates required env vars are present.
"""

import json
import asyncio
import os
import logging
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
from alert_worker import run_all_alerts
from whatsapp import send_whatsapp

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
    allow_headers=["Content-Type", "X-Internal-Secret", "X-Webhook-Secret"],
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
# WhatsApp sending is currently a stub (see whatsapp.py) — no BSP account
# exists yet. Everything below is fully functional and testable end-to-end;
# only the actual outbound WhatsApp call is a no-op logger until an AiSensy
# (or similar) integration is wired in.

PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


class AlertRequest(BaseModel):
    phone: str
    locality: str = Field(min_length=1, max_length=100)
    bhk: str = Field(min_length=1, max_length=20)
    max_rent: int = Field(gt=0, le=10_000_000)


@app.post("/alerts")
@limiter.limit("5/hour")
async def create_alert(request: Request, body: AlertRequest):
    phone = body.phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=422, detail="Invalid phone number")

    search_id = await alerts_store.create_saved_search(
        phone, body.locality.strip(), body.bhk.strip(), body.max_rent
    )
    await send_whatsapp(
        phone,
        f"RentRadar: Confirm alerts for {body.bhk} in {body.locality} "
        f"under ₹{body.max_rent:,}/mo? Reply YES to activate.",
    )
    return {"id": search_id, "status": "pending_confirmation"}


class WebhookRequest(BaseModel):
    phone: str
    message: str = Field(max_length=500)


@app.post("/alerts/webhook")
@limiter.limit("60/minute")
async def alerts_webhook(request: Request, body: WebhookRequest, x_webhook_secret: str = Header(default="")):
    """
    Inbound WhatsApp message handler. Point your BSP's webhook here once one
    exists. A "YES" reply confirms the phone's most recent pending saved search
    — this doubles as WhatsApp's required opt-in confirmation.

    Requires ALERTS_WEBHOOK_SECRET to be set — returns 503 if it isn't, so this
    can't run unprotected. This is a placeholder shared-secret check; once a
    real BSP is wired up, replace it with verification of THEIR signature
    header (e.g. an HMAC over the request body) rather than a static secret,
    since a static value can't prove the request actually came from WhatsApp.
    """
    secret = os.getenv("ALERTS_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    if x_webhook_secret != secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.message.strip().upper() != "YES":
        return {"status": "ignored"}
    confirmed_id = await alerts_store.confirm_latest_for_phone(body.phone.strip())
    if confirmed_id is None:
        return {"status": "no_pending_search"}
    return {"status": "confirmed", "id": confirmed_id}


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
