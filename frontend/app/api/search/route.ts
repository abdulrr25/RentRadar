/**
 * Next.js route handler — proxies SSE stream from FastAPI backend.
 * Uses BACKEND_API_URL (server-only) or falls back to NEXT_PUBLIC_API_URL.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.json();

  // Prefer a server-only env var so the backend URL never hits the client bundle
  const apiUrl =
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";

  try {
    const upstream = await fetch(`${apiUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
    const message = err instanceof Error ? err.message : String(err);
    return new Response(
      `data: ${JSON.stringify({ type: "error", message: `Backend unreachable: ${message}` })}\n\n`,
      {
        status: 200, // keep 200 so the SSE stream stays open for the error event
        headers: { "Content-Type": "text/event-stream" },
      }
    );
  }
}
