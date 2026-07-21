"use client";

import { useState } from "react";

interface Props {
  query?: string;
}

type Rating = "up" | "down" | null;
type SubmitState = "idle" | "sending" | "sent" | "error";

export default function FeedbackWidget({ query }: Props) {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState<Rating>(null);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<SubmitState>("idle");

  const reset = () => {
    setOpen(false);
    setRating(null);
    setMessage("");
    setState("idle");
  };

  const submit = async () => {
    if (!rating) return;
    setState("sending");
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, message, query: query ?? "" }),
      });
      const data = await res.json();
      setState(data.status === "ok" ? "sent" : "error");
    } catch {
      setState("error");
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open && (
        <div
          className="card-enter mb-3 w-72 rounded-2xl border border-slate-200 bg-white p-5"
          style={{ boxShadow: "0 12px 40px -8px rgba(15,23,42,0.18), 0 4px 12px -4px rgba(15,23,42,0.1)" }}
        >
          {state === "sent" ? (
            <div className="py-2 text-center">
              <p className="text-2xl">🙏</p>
              <p className="mt-2 text-sm font-semibold text-slate-800">Thanks for the feedback!</p>
              <button onClick={reset} className="mt-3 text-xs font-medium text-brand-600 hover:text-brand-700">
                Close
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-900">How's RentRadar working for you?</p>
                <button
                  onClick={reset}
                  aria-label="Close feedback"
                  className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                >
                  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => setRating("up")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-2 text-sm font-medium transition ${
                    rating === "up"
                      ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                      : "border-slate-200 text-slate-500 hover:border-slate-300"
                  }`}
                >
                  👍 Useful
                </button>
                <button
                  onClick={() => setRating("down")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-2 text-sm font-medium transition ${
                    rating === "down"
                      ? "border-red-300 bg-red-50 text-red-700"
                      : "border-slate-200 text-slate-500 hover:border-slate-300"
                  }`}
                >
                  👎 Not quite
                </button>
              </div>

              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Anything specific? (optional)"
                aria-label="Additional feedback (optional)"
                rows={3}
                maxLength={1000}
                className="mt-3 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 placeholder-slate-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-brand-50"
              />

              {state === "error" && (
                <p className="mt-2 text-xs text-red-600">Couldn't send — please try again.</p>
              )}

              <button
                onClick={submit}
                disabled={!rating || state === "sending"}
                className="mt-3 w-full rounded-xl py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)" }}
              >
                {state === "sending" ? "Sending…" : "Send feedback"}
              </button>
            </>
          )}
        </div>
      )}

      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:text-brand-700"
          style={{ boxShadow: "0 4px 16px -4px rgba(15,23,42,0.15), 0 1px 4px rgba(15,23,42,0.08)" }}
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Feedback
        </button>
      )}
    </div>
  );
}
