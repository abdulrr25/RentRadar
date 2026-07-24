"use client";

import { useEffect, useState } from "react";

const DISMISS_KEY = "rentradar-status-banner-dismissed";
const POLL_INTERVAL_MS = 60_000;

export default function StatusBanner() {
  const [degraded, setDegraded] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (!cancelled) setDegraded(data.status === "degraded");
      } catch {
        // Silently ignore — this banner is informational, never blocks the page.
      }
    };

    check();
    const interval = setInterval(check, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  useEffect(() => {
    if (degraded && sessionStorage.getItem(DISMISS_KEY) === "1") {
      setDismissed(true);
    }
  }, [degraded]);

  if (!degraded || dismissed) return null;

  const dismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  };

  return (
    <div className="border-b border-amber-200 bg-amber-50">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:px-6">
        <svg viewBox="0 0 24 24" className="h-4 w-4 flex-shrink-0 text-amber-500" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <p className="flex-1 text-xs font-medium text-amber-800 sm:text-sm">
          Live listing sources are temporarily unavailable — searches may return limited or no results right now. We're aware and it usually resolves on its own shortly.
        </p>
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-amber-500 transition hover:bg-amber-100"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
