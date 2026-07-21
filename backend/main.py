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

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv

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


app = FastAPI(title="RentRadar API", version="1.0.0", lifespan=lifespan)

# CORS: allow local dev + any Vercel preview/prod deployment
# Add EXTRA_ORIGINS env var (comma-separated) for custom domains
_extra = [o.strip() for o in os.getenv("EXTRA_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *_extra],
    allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"service": "RentRadar API", "status": "ok", "docs": "/docs"}


class SearchRequest(BaseModel):
    query: str


@app.post("/search")
async def search(request: SearchRequest):
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
            parsed = parse_query(request.query)
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
            logger.exception("Pipeline error for query: %s", request.query)
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
    message: str = ""
    query: str = ""


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    """Append feedback as a JSON line. Best-effort — never blocks the UI on failure."""
    entry = {
        "ts": int(time.time()),
        "rating": request.rating,
        "message": request.message.strip()[:1000],
        "query": request.query.strip()[:300],
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
    locality: str
    bhk: str
    max_rent: int = Field(gt=0)


@app.post("/alerts")
async def create_alert(request: AlertRequest):
    phone = request.phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=422, detail="Invalid phone number")

    search_id = await alerts_store.create_saved_search(
        phone, request.locality.strip(), request.bhk.strip(), request.max_rent
    )
    await send_whatsapp(
        phone,
        f"RentRadar: Confirm alerts for {request.bhk} in {request.locality} "
        f"under ₹{request.max_rent:,}/mo? Reply YES to activate.",
    )
    return {"id": search_id, "status": "pending_confirmation"}


class WebhookRequest(BaseModel):
    phone: str
    message: str


@app.post("/alerts/webhook")
async def alerts_webhook(request: WebhookRequest):
    """
    Inbound WhatsApp message handler. Point your BSP's webhook here once one
    exists. A "YES" reply confirms the phone's most recent pending saved search
    — this doubles as WhatsApp's required opt-in confirmation.
    """
    if request.message.strip().upper() != "YES":
        return {"status": "ignored"}
    confirmed_id = await alerts_store.confirm_latest_for_phone(request.phone.strip())
    if confirmed_id is None:
        return {"status": "no_pending_search"}
    return {"status": "confirmed", "id": confirmed_id}


@app.delete("/alerts/{search_id}")
async def delete_alert(search_id: str):
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
