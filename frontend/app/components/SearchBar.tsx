"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  "2BHK near Bellandur under ₹25,000",
  "1BHK Whitefield under ₹18,000",
  "3BHK HSR Layout under ₹45,000",
  "2BHK Koramangala under ₹30,000",
];

export default function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");

  const handleSearch = () => { if (query.trim()) onSearch(query.trim()); };
  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => { if (e.key === "Enter") handleSearch(); };
  const canSearch = !loading && Boolean(query.trim());

  return (
    <div className="mx-auto w-full max-w-2xl space-y-3.5">

      {/* Input */}
      <div
        className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 transition-all focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-50"
        style={{ boxShadow: "0 1px 4px rgba(15,23,42,0.07), 0 4px 16px -4px rgba(15,23,42,0.06)" }}
      >
        <span className="pl-3 text-slate-400">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
          </svg>
        </span>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="e.g. 2BHK near Bellandur under ₹25,000"
          disabled={loading}
          className="flex-1 bg-transparent px-2 py-3.5 text-base text-slate-900 placeholder-slate-400 focus:outline-none disabled:opacity-60"
        />

        <button
          onClick={handleSearch}
          disabled={!canSearch}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-all active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)",
            boxShadow: canSearch ? "0 1px 3px rgba(79,70,229,0.4), 0 4px 12px -2px rgba(79,70,229,0.25)" : "none",
          }}
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              <span className="hidden sm:inline">Scanning…</span>
            </>
          ) : (
            <>
              <span className="hidden sm:inline">Search</span>
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </>
          )}
        </button>
      </div>

      {/* Example chips */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none -mx-1 px-1 pb-0.5">
        <span className="flex-shrink-0 text-xs text-slate-400 font-medium">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setQuery(ex)}
            disabled={loading}
            className="flex-shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 font-medium transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-40"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
