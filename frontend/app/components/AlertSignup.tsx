"use client";

import { useState } from "react";

interface Props {
  locality: string;
  bhk: string;
  maxRent: number;
}

type Channel = "telegram" | "webpush" | "email";
type Status = "idle" | "working" | "confirmed" | "pending" | "error";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function urlBase64ToUint8Array(base64Url: string): Uint8Array {
  const padding = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

async function createAlert(payload: Record<string, unknown>) {
  const res = await fetch("/api/alerts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { ok: res.ok, data: await res.json().catch(() => ({})) };
}

const CHANNELS: { id: Channel; label: string; icon: string }[] = [
  { id: "telegram", label: "Telegram", icon: "✈️" },
  { id: "webpush", label: "Browser", icon: "🔔" },
  { id: "email", label: "Email", icon: "✉️" },
];

export default function AlertSignup({ locality, bhk, maxRent }: Props) {
  const [dismissed, setDismissed] = useState(false);
  const [channel, setChannel] = useState<Channel | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [email, setEmail] = useState("");
  const [telegramLink, setTelegramLink] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const base = { locality, bhk, max_rent: maxRent };

  const startTelegram = async () => {
    setStatus("working");
    setErrorMsg(null);
    const { ok, data } = await createAlert({ channel: "telegram", ...base });
    if (!ok || !data.telegram_link) {
      setStatus("error");
      setErrorMsg(ok ? "Telegram alerts aren't set up yet." : "Couldn't start — please try again.");
      return;
    }
    setTelegramLink(data.telegram_link);
    window.open(data.telegram_link, "_blank", "noopener,noreferrer");
    setStatus("pending");
  };

  const startWebPush = async () => {
    setStatus("working");
    setErrorMsg(null);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        throw new Error("Push notifications aren't supported in this browser.");
      }
      const publicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
      if (!publicKey) throw new Error("Browser alerts aren't set up yet.");

      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("Notification permission was denied.");

      const registration = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        // Runtime type is correct (a plain Uint8Array, exactly what the Push
        // API expects) — the mismatch is lib.dom.d.ts's generic ArrayBuffer
        // vs ArrayBufferLike typing, not an actual type error.
        applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
      });

      const { ok } = await createAlert({ channel: "webpush", target: JSON.stringify(subscription), ...base });
      if (!ok) throw new Error("Couldn't save your subscription — please try again.");
      setStatus("confirmed");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  const startEmail = async () => {
    if (!EMAIL_RE.test(email.trim())) return;
    setStatus("working");
    setErrorMsg(null);
    const { ok, data } = await createAlert({ channel: "email", target: email.trim(), ...base });
    if (!ok || data.status !== "pending_confirmation") {
      setStatus("error");
      setErrorMsg("Couldn't send — please try again.");
      return;
    }
    setStatus("pending");
  };

  if (dismissed) return null;

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-brand-900">Get notified about new matches</p>
          <p className="mt-0.5 text-xs text-brand-700">
            Get pinged the moment a new {bhk} appears in {locality} under ₹{maxRent.toLocaleString("en-IN")}.
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-brand-400 transition hover:bg-brand-100 hover:text-brand-600"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {status === "confirmed" && (
        <p className="mt-3 flex items-center gap-2 text-sm text-brand-800">
          <span>✅</span> You're subscribed — we'll notify you here in the browser.
        </p>
      )}

      {status === "pending" && channel === "telegram" && (
        <p className="mt-3 text-sm text-brand-800">
          Almost there — tap <strong>Start</strong> in the Telegram chat that just opened to finish.{" "}
          {telegramLink && (
            <a href={telegramLink} target="_blank" rel="noopener noreferrer" className="underline">
              Open it again
            </a>
          )}
        </p>
      )}

      {status === "pending" && channel === "email" && (
        <p className="mt-3 text-sm text-brand-800">
          Almost there — check <strong>{email}</strong> for a confirmation link.
        </p>
      )}

      {(status === "idle" || status === "working" || status === "error") && (
        <>
          <div className="mt-3 flex gap-2">
            {CHANNELS.map((c) => (
              <button
                key={c.id}
                onClick={() => { setChannel(c.id); setErrorMsg(null); setStatus("idle"); }}
                className={`flex-1 rounded-lg border py-2 text-sm font-medium transition ${
                  channel === c.id
                    ? "border-brand-400 bg-white text-brand-700"
                    : "border-brand-200 text-brand-600 hover:border-brand-300"
                }`}
              >
                {c.icon} {c.label}
              </button>
            ))}
          </div>

          {channel === "telegram" && (
            <button
              onClick={startTelegram}
              disabled={status === "working"}
              className="mt-3 w-full rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)" }}
            >
              {status === "working" ? "Opening Telegram…" : "Connect via Telegram"}
            </button>
          )}

          {channel === "webpush" && (
            <button
              onClick={startWebPush}
              disabled={status === "working"}
              className="mt-3 w-full rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)" }}
            >
              {status === "working" ? "Requesting permission…" : "Enable browser alerts"}
            </button>
          )}

          {channel === "email" && (
            <div className="mt-3 flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                aria-label="Email address for alerts"
                className="min-w-0 flex-1 rounded-lg border border-brand-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-brand-400 focus:outline-none focus:ring-4 focus:ring-brand-100"
              />
              <button
                onClick={startEmail}
                disabled={!EMAIL_RE.test(email.trim()) || status === "working"}
                className="flex-shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)" }}
              >
                {status === "working" ? "Sending…" : "Notify me"}
              </button>
            </div>
          )}

          {status === "error" && errorMsg && (
            <p className="mt-2 text-xs text-red-600">{errorMsg}</p>
          )}
        </>
      )}
    </div>
  );
}
