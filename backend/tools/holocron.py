"""
Wire tool — pre-built structured actions via Anakin's /v1/wire/task endpoint.
Wire actions are async: POST returns a job_id, then poll /v1/wire/jobs/{id}
until status is 'completed' or 'failed'.

Verified action IDs (from wire_catalog / wire_discover):
  rt_search  → Reddit post search
  hn_search  → Hacker News search
  gn_search  → Google News search
"""

import asyncio
import httpx
import os

WIRE_BASE = "https://api.anakin.io/v1/wire"
POLL_INTERVAL = 1.5   # seconds between polls
POLL_TIMEOUT  = 25.0  # max seconds to wait for a job


def _headers() -> dict:
    """Read API key at call time — never captured at module import."""
    return {
        "X-API-Key": os.getenv("ANAKIN_API_KEY", ""),
        "Content-Type": "application/json",
    }


async def _poll_job(client: httpx.AsyncClient, job_id: str) -> dict:
    """Poll a Wire job until completed/failed or timeout."""
    deadline = asyncio.get_event_loop().time() + POLL_TIMEOUT
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"{WIRE_BASE}/jobs/{job_id}", headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "completed":
            return data.get("result", data)
        if status == "failed":
            raise RuntimeError(f"Wire job failed: {data.get('error', 'unknown')}")
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Wire job {job_id} timed out after {POLL_TIMEOUT}s")


async def wire_action(action_id: str, params: dict, source_name: str) -> dict:
    """Submit a Wire action and poll until result is ready."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
            # Submit job
            resp = await client.post(
                f"{WIRE_BASE}/task",
                headers=_headers(),
                json={"action_id": action_id, "params": params},
            )
            resp.raise_for_status()
            job = resp.json()

            job_id = job.get("job_id")
            if not job_id:
                # Some actions return results immediately
                return {"source": source_name, "status": "ok", "data": job}

            # Poll for result
            result = await _poll_job(client, job_id)
            return {"source": source_name, "status": "ok", "data": result}

    except Exception as e:
        return {"source": source_name, "status": "error", "data": str(e)}


async def fetch_reddit(locality: str, bhk: str) -> dict:
    """Wire → rt_search — Reddit posts about this locality."""
    query = f"{locality} Bangalore rent {bhk} review"
    return await wire_action(
        action_id="rt_search",
        params={"query": query, "limit": 15, "sort": "relevance", "time": "year"},
        source_name="Reddit",
    )


async def fetch_google_news(locality: str) -> dict:
    """Wire → gn_search — Google News for rental market signals."""
    return await wire_action(
        action_id="gn_search",
        params={"query": f"{locality} Bangalore rent property", "limit": 10},
        source_name="Google News",
    )


async def fetch_hackernews(locality: str) -> dict:
    """Wire → hn_search — Hacker News for tech-worker perspectives."""
    return await wire_action(
        action_id="hn_search",
        params={"query": f"Bangalore {locality} living"},
        source_name="Hacker News",
    )
