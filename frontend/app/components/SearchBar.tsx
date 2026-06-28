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
    <div className="w-full max-w-2xl mx-auto space-y-4">
      <div className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="2BHK near Bellandur under ₹25,000"
          className="
            flex-1 bg-[#111118] border border-[#1e1e2e] rounded-xl
            px-5 py-4 text-slate-100 placeholder-slate-500
            focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/60
            text-base transition-all duration-200
          "
          disabled={loading}
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="
            px-6 py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900
            disabled:cursor-not-allowed text-white font-semibold rounded-xl
            transition-all duration-200 whitespace-nowrap
            focus:outline-none focus:ring-2 focus:ring-indigo-400
          "
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Scanning…
            </span>
          ) : (
            "Search"
          )}
        </button>
      </div>

      {/* Example queries */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setQuery(ex)}
            className="
              text-xs px-3 py-1.5 rounded-lg bg-[#111118] border border-[#1e1e2e]
              text-slate-400 hover:text-slate-200 hover:border-indigo-500/40
              transition-all duration-150
            "
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
