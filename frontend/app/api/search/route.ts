/**
 * Next.js route handler — proxies SSE stream from FastAPI backend.
 *
 * The browser calls /api/search (Next.js) which proxies to BACKEND_API_URL (FastAPI).
 * The backend URL never reaches the browser — it stays server-side only.
 */

import { NextRequest } from "next/server";
import { classifyBackendError } from "../../../lib/backendErrors";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.json();

  // Server-only env var — set BACKEND_API_URL in .env.local (local) or Vercel dashboard (prod)
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

  try {
    // AbortSignal.timeout (not a manual AbortController) so the failure
    // arrives as a TimeoutError rather than a generic AbortError — that's
    // what lets classifyBackendError tell "server still waking up" apart
    // from "something else broke". 55s keeps us under Vercel's 60s limit.
    const upstream = await fetch(`${apiUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(55_000),
    });

    if (!upstream.body) {
      return new Response(
        JSON.stringify({ error: "Backend returned empty response" }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        Connection: "keep-alive",
      },
    });
  } catch (err) {
    // Never surface the raw exception text ("fetch failed", "ECONNREFUSED")
    // to the browser — it reads as a broken product when the usual cause is
    // just a Render free-tier cold start. Log the real error, send a
    // human-readable one.
    console.error("[/api/search] upstream request failed:", err);
    const { code, message } = classifyBackendError(err);
    return new Response(
      `data: ${JSON.stringify({ type: "error", code, message })}\n\n`,
      {
        status: 200, // keep 200 so the SSE stream stays open for the error event
        headers: { "Content-Type": "text/event-stream" },
      }
    );
  }
}
