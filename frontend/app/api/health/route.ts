/**
 * Next.js route handler — proxies backend health status to the browser.
 * Used by the frontend to show a proactive banner when live sources are
 * degraded (e.g. the search backend is down), before anyone even searches.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: NextRequest) {
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

  try {
    const upstream = await fetch(`${apiUrl}/health`, {
      signal: AbortSignal.timeout(8_000),
    });
    const data = await upstream.json().catch(() => ({ status: "unknown" }));
    return new Response(JSON.stringify(data), {
      status: 200, // always 200 — this endpoint reports status, doesn't fail the page
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ status: "unknown" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
}
