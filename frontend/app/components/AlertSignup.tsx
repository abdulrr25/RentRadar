"use client";

import { useState } from "react";

interface Props {
  locality: string;
  bhk: string;
  maxRent: number;
}

type State = "idle" | "sending" | "pending" | "error";

const PHONE_RE = /^\+?[0-9]{10,15}$/;

export default function AlertSignup({ locality, bhk, maxRent }: Props) {
  const [phone, setPhone] = useState("");
  const [state, setState] = useState<State>("idle");
  const [dismissed, setDismissed] = useState(false);

  const valid = PHONE_RE.test(phone.trim());

  const submit = async () => {
    if (!valid) return;
    setState("sending");
    try {
      const res = await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), locality, bhk, max_rent: maxRent }),
      });
      const data = await res.json();
      setState(data.status === "pending_confirmation" ? "pending" : "error");
    } catch {
      setState("error");
    }
  };

  if (dismissed) return null;

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 sm:p-5">
      {state === "pending" ? (
        <div className="flex items-start gap-3">
          <span className="text-lg">✅</span>
          <p className="text-sm text-brand-800">
            Almost there — we've sent a WhatsApp message to <strong>{phone}</strong>. Reply{" "}
            <strong>YES</strong> to activate alerts for new {bhk} matches in {locality} under ₹{maxRent.toLocaleString("en-IN")}.
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-brand-900">
                Never miss a match like this
              </p>
              <p className="mt-0.5 text-xs text-brand-700">
                Get a free WhatsApp ping the moment a new {bhk} appears in {locality} under ₹{maxRent.toLocaleString("en-IN")}.
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

          <div className="mt-3 flex gap-2">
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
              aria-label="Phone number for WhatsApp alerts"
              className="min-w-0 flex-1 rounded-lg border border-brand-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-brand-400 focus:outline-none focus:ring-4 focus:ring-brand-100"
            />
            <button
              onClick={submit}
              disabled={!valid || state === "sending"}
              className="flex-shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)" }}
            >
              {state === "sending" ? "Sending…" : "Notify me"}
            </button>
          </div>

          {state === "error" && (
            <p className="mt-2 text-xs text-red-600">Couldn't send — please try again.</p>
          )}
        </>
      )}
    </div>
  );
}
