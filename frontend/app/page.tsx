"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import SearchBar from "./components/SearchBar";
import SourceIndicators from "./components/SourceIndicators";
import RentRadarCard from "./components/RentRadarCard";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

const ALL_SOURCES = [
  "Reddit", "Google News", "Hacker News",
  "NoBroker", "MagicBricks", "Housing.com",
];

export default function Home() {
  const [loading, setLoading]           = useState(false);
  const [sources, setSources]           = useState<string[]>([]);
  const [statuses, setStatuses]         = useState<Record<string, SourceStatus>>({});
  const [brief, setBrief]               = useState<string | null>(null);
  const [error, setError]               = useState<string | null>(null);
  const [parsedQuery, setParsedQuery]   = useState<Record<string, any> | null>(null);
  const abortRef                        = useRef<AbortController | null>(null);

  // Abort any in-flight request on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const handleSearch = useCallback(async (query: string) => {
    // Cancel any in-flight search
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setBrief(null);
    setError(null);
    setParsedQuery(null);
    setSources([]);
    setStatuses({});

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      });

      if (!res.body) {
        throw new Error("Response body is empty — backend may be down.");
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));

            switch (event.type) {
              case "parsed":
                setParsedQuery(event.data);
                break;

              case "fetching":
                setSources(event.sources ?? ALL_SOURCES);
                setStatuses(
                  Object.fromEntries((event.sources ?? ALL_SOURCES).map((s: string) => [s, "fetching"]))
                );
                break;

              case "source_complete":
                setStatuses((prev) => ({
                  ...prev,
                  [event.source]: event.status === "ok" ? "ok" : "error",
                }));
                break;

              case "brief":
                setBrief(event.data);
                break;

              case "done":
                setLoading(false);
                break;

              case "error":
                setError(event.message ?? "Something went wrong.");
                setLoading(false);
                break;
            }
          } catch {
            // malformed SSE line — ignore
          }
        }
      }
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setError("Failed to connect to the server. Make sure the backend is running.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <main className="min-h-screen px-4 py-16 flex flex-col items-center">
      {/* Hero */}
      <div className="text-center mb-12 space-y-3">
        <div className="inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-700/40 text-indigo-300 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Powered by Anakin Wire · Universal Scraper · Llama 3.1 70B
        </div>
        <h1 className="text-5xl font-bold tracking-tight text-slate-100">
          Rent<span className="text-indigo-400">Radar</span>
        </h1>
        <p className="text-lg text-slate-400 max-w-md mx-auto">
          Find your Bangalore flat. Instantly.
          <br />
          <span className="text-slate-500 text-base">
            AI-powered intelligence from 7 live sources — listings, Reddit, trends & scam alerts.
          </span>
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} loading={loading} />

      {/* Source pills */}
      {sources.length > 0 && (
        <div className="mt-8 w-full max-w-2xl">
          <SourceIndicators sources={sources} statuses={statuses} />
        </div>
      )}

      {/* Parsed query chip */}
      {parsedQuery && (
        <div className="mt-4 flex flex-wrap gap-2 text-xs justify-center">
          {[
            `📍 ${parsedQuery.locality}`,
            `🛏 ${parsedQuery.bhk}`,
            `💰 max ₹${parsedQuery.max_rent?.toLocaleString("en-IN")}`,
          ].map((chip) => (
            <span
              key={chip}
              className="px-3 py-1 rounded-full bg-[#111118] border border-[#1e1e2e] text-slate-400"
            >
              {chip}
            </span>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mt-8 w-full max-w-2xl p-4 rounded-xl bg-red-950/40 border border-red-700/40 text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Results */}
      {brief && <RentRadarCard rawBrief={brief} />}

      {/* Loading skeleton */}
      {loading && !brief && (
        <div className="mt-8 w-full max-w-2xl space-y-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-[#111118] border border-[#1e1e2e] animate-pulse"
              style={{ opacity: 1 - i * 0.25 }}
            />
          ))}
        </div>
      )}

      {/* Footer */}
      <footer className="mt-20 text-center text-xs text-slate-600">
        RentRadar · Built for Bangalore tenants · Data refreshed on every search
      </footer>
    </main>
  );
}
