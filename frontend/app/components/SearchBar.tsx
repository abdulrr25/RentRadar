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
    <div className="mx-auto w-full max-w-2xl space-y-4">
      {/* Input container */}
      <div className="group relative">
        {/* Animated glow on focus */}
        <div
          className="pointer-events-none absolute -inset-[1.5px] rounded-[18px] opacity-0 transition-opacity duration-400 group-focus-within:opacity-100"
          style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.55), rgba(139,92,246,0.35))", filter: "blur(6px)" }}
        />
        {/* Input shell */}
        <div
          className="relative flex items-center gap-2 rounded-2xl border transition-all duration-300 focus-within:border-indigo-500/45 p-2"
          style={{ background: "rgba(13,13,28,0.9)", borderColor: "rgba(255,255,255,0.09)" }}
        >
          {/* Search icon */}
          <span className="pl-3 text-slate-600">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
            </svg>
          </span>

          {/* Text input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="e.g. 2BHK near Bellandur under ₹25,000"
            disabled={loading}
            className="flex-1 bg-transparent px-2 py-3.5 text-base text-slate-100 placeholder-slate-600 focus:outline-none disabled:opacity-60"
          />

          {/* Button */}
          <button
            onClick={handleSearch}
            disabled={!canSearch}
            className="inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-all duration-200 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              background: canSearch
                ? "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)"
                : "rgba(99,102,241,0.25)",
              boxShadow: canSearch ? "0 0 22px -6px rgba(99,102,241,0.65), 0 4px 12px -4px rgba(99,102,241,0.3)" : "none",
            }}
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/25 border-t-white" />
                <span className="hidden sm:inline text-white/80">Scanning…</span>
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
      </div>

      {/* Example chips — horizontal scroll on mobile */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none -mx-1 px-1 pb-0.5">
        <span className="flex-shrink-0 text-xs text-slate-600">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setQuery(ex)}
            disabled={loading}
            className="flex-shrink-0 rounded-lg border border-white/[0.07] px-3 py-1.5 text-xs text-slate-500 transition-all hover:border-indigo-500/30 hover:bg-indigo-500/[0.07] hover:text-slate-200 disabled:opacity-40"
            style={{ background: "rgba(255,255,255,0.02)" }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
