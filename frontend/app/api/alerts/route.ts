/**
 * Next.js route handler — proxies saved-search alert signups to FastAPI backend.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

  try {
    const upstream = await fetch(`${apiUrl}/alerts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });

    const data = await upstream.json().catch(() => ({ status: "error" }));
    return new Response(JSON.stringify(data), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ status: "error" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
