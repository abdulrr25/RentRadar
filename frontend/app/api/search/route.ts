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
// Without this, Vercel kills the function at its platform default (10s on
// Hobby) long before the 55s AbortSignal.timeout below ever fires — exactly
// during the cold-start case (backend waking up, up to ~60s) this route and
// the frontend's cold-start hint are built to tolerate. Matches the 55s
// upstream budget plus headroom for this route's own overhead, within
// Vercel's Hobby-plan ceiling.
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  const body = await req.json();

  // Server-only env var — set BACKEND_API_URL in .env.local (local) or Vercel dashboard (prod)
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

  // The backend's rate limiter keys off this — otherwise it sees this
  // route's own outbound connection for every visitor (see backend/main.py).
  const forwardedFor = req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip");

  try {
    // AbortSignal.timeout (not a manual AbortController) so the failure
    // arrives as a TimeoutError rather than a generic AbortError — that's
    // what lets classifyBackendError tell "server still waking up" apart
    // from "something else broke". 55s keeps us under Vercel's 60s limit.
    const upstream = await fetch(`${apiUrl}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(55_000),
    });

    if (!upstream.body) {
      return new Response(
        JSON.stringify({ error: "Backend returned empty response" }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    // Anything other than 2xx here isn't an SSE stream — e.g. slowapi's 429
    // is a plain JSON body ({"error": "..."}), not "data: {...}" lines. The
    // client's reader only ever looks for "data: " lines, so handing that
    // straight through used to make a rate-limited or crashed search fail
    // completely silently: the loading state just stopped with no brief and
    // no error, which read as the product doing nothing. Normalize it into
    // the same SSE error event the client already renders.
    if (!upstream.ok) {
      const message =
        upstream.status === 429
          ? "RentRadar is getting a lot of searches right now — please wait a few minutes and try again."
          : "Something went wrong while running that search. Please try again.";
      return new Response(
        `data: ${JSON.stringify({ type: "error", message })}\n\n`,
        { status: 200, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } }
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
