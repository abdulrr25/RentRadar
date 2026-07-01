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

  const handleSearch = () => {
    if (query.trim()) onSearch(query.trim());
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      {/* Input */}
      <div className="group relative">
        <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-indigo-600/40 to-violet-600/40 opacity-0 blur transition duration-300 group-focus-within:opacity-100" />
        <div className="relative flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] p-2 backdrop-blur-xl transition focus-within:border-indigo-500/50">
          <span className="pl-3 text-slate-500">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="2BHK near Bellandur under ₹25,000"
            disabled={loading}
            className="flex-1 bg-transparent px-1 py-3 text-base text-slate-100 placeholder-slate-500 focus:outline-none disabled:opacity-60"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-glow-sm transition hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span className="hidden sm:inline">Scanning…</span>
              </>
            ) : (
              <>
                <span>Search</span>
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Example chips — scrollable row on mobile */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none -mx-1 px-1">
        <span className="flex-shrink-0 py-1.5 text-xs text-slate-500">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setQuery(ex)}
            disabled={loading}
            className="flex-shrink-0 rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400 transition hover:border-indigo-500/40 hover:bg-indigo-500/10 hover:text-slate-100 disabled:opacity-50"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
