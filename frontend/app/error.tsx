"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("Unhandled frontend error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 border border-red-200">
        <svg viewBox="0 0 24 24" className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>
      <h1 className="mt-5 font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
        Something went wrong
      </h1>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        An unexpected error interrupted this page. It's been logged — try again, or head back to search.
      </p>
      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-all active:scale-[0.97]"
          style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)", boxShadow: "0 1px 3px rgba(79,70,229,0.4), 0 4px 12px -2px rgba(79,70,229,0.25)" }}
        >
          Try again
        </button>
        <a href="/" className="text-sm font-medium text-slate-500 hover:text-slate-700">
          Back to search
        </a>
      </div>
    </div>
  );
}
