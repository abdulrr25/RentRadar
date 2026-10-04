/**
 * Next.js route handler — proxies feedback submissions to FastAPI backend.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
  // The backend's rate limiter keys off this — otherwise it sees this
  // route's own outbound connection for every visitor (see backend/main.py).
  const forwardedFor = req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip");

  try {
    const upstream = await fetch(`${apiUrl}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
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
