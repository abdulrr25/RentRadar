/**
 * Next.js route handler — proxies SSE stream from FastAPI backend.
 *
 * The browser calls /api/search (Next.js) which proxies to BACKEND_API_URL (FastAPI).
 * The backend URL never reaches the browser — it stays server-side only.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.json();

  // Server-only env var — set BACKEND_API_URL in .env.local (local) or Vercel dashboard (prod)
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:9000";

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
