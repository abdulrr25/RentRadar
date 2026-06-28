"""
RentRadar FastAPI server.

POST /search  — accepts a natural language query, streams SSE events back.
GET  /health  — liveness check; validates required env vars are present.
"""

import json
import asyncio
import os
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend dir first, then fall back to project root
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

from parser import parse_query
from agent import agent

app = FastAPI(title="RentRadar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
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
      error           — pipeline error (non-fatal partial errors are swallowed)
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
            tb = traceback.format_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'detail': tb})}\n\n"

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
