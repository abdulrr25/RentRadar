"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import SearchBar from "./components/SearchBar";
import SourceIndicators from "./components/SourceIndicators";
import RentRadarCard from "./components/RentRadarCard";
import HowItWorks from "./components/HowItWorks";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

const ALL_SOURCES = [
  "Reddit", "Google News", "Hacker News",
  "NoBroker", "OLX", "Housing.com",
];

export default function Home() {
  const [loading, setLoading]         = useState(false);
  const [sources, setSources]         = useState<string[]>([]);
  const [statuses, setStatuses]       = useState<Record<string, SourceStatus>>({});
  const [brief, setBrief]             = useState<string | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [parsedQuery, setParsedQuery] = useState<Record<string, any> | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const abortRef                      = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const handleSearch = useCallback(async (query: string) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setHasSearched(true);
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

      if (!res.body) throw new Error("Response body is empty — backend may be down.");
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
            /* malformed SSE line — ignore */
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
    <div className="relative min-h-screen flex flex-col">
      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-radar-bg/70 backdrop-blur-xl">
        <div className="mx-auto max-w-6xl px-5 h-16 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 group">
            <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-glow-sm">
              <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" />
                <path d="m21 21-4.3-4.3" />
              </svg>
            </span>
            <span className="font-display text-lg font-bold tracking-tight text-white">
              Rent<span className="gradient-text">Radar</span>
            </span>
          </a>

          <div className="flex items-center gap-4">
            <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              6 live sources
            </span>
            <a
              href="https://github.com/abdulrr25/RentRadar"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-white/20 hover:text-white"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.4-3.9-1.4-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z" /></svg>
              GitHub
            </a>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* ── Hero ──────────────────────────────────────────────────── */}
        <section className="mx-auto max-w-3xl px-5 pt-16 pb-8 sm:pt-24 text-center">
          <div className="rise inline-flex items-center gap-2 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-medium text-indigo-200">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Anakin Wire · Universal Scraper · Llama 3.3 70B
          </div>

          <h1 className="rise delay-1 mt-7 font-display text-5xl sm:text-6xl font-extrabold leading-[1.05] tracking-tight text-white">
            Find your Bangalore flat,
            <br className="hidden sm:block" />
            <span className="gradient-text"> intelligently.</span>
          </h1>

          <p className="rise delay-2 mx-auto mt-5 max-w-xl text-base sm:text-lg leading-relaxed text-slate-400">
            One question. RentRadar scans six live sources in parallel and returns
            ranked listings, locality scores, price trends and scam alerts — in seconds.
          </p>

          <div className="rise delay-3 mt-9">
            <SearchBar onSearch={handleSearch} loading={loading} />
          </div>
        </section>

        {/* ── Live status + parsed query ────────────────────────────── */}
        {sources.length > 0 && (
          <section className="mx-auto max-w-2xl px-5 fade-in">
            <SourceIndicators sources={sources} statuses={statuses} />
            {parsedQuery && (
              <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
                {[
                  `📍 ${parsedQuery.locality}`,
                  `🛏 ${parsedQuery.bhk}`,
                  `💰 max ₹${parsedQuery.max_rent?.toLocaleString("en-IN")}`,
                ].map((chip) => (
                  <span key={chip} className="glass rounded-full px-3 py-1 text-slate-300">
                    {chip}
                  </span>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ── Error ─────────────────────────────────────────────────── */}
        {error && (
          <section className="mx-auto mt-8 max-w-2xl px-5">
            <div className="rounded-2xl border border-red-700/40 bg-red-950/30 p-4 text-sm text-red-300">
              ⚠️ {error}
            </div>
          </section>
        )}

        {/* ── Results ───────────────────────────────────────────────── */}
        <section className="mx-auto max-w-2xl px-5 pb-20">
          {brief && <RentRadarCard rawBrief={brief} />}

          {loading && !brief && (
            <div className="mt-8 space-y-4">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="shimmer h-20 rounded-2xl border border-white/[0.06] bg-white/[0.02]"
                  style={{ opacity: 1 - i * 0.22 }}
                />
              ))}
            </div>
          )}
        </section>

        {/* ── How it works (only before a search) ───────────────────── */}
        {!hasSearched && <HowItWorks />}
      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.06] bg-radar-bg/40">
        <div className="mx-auto max-w-6xl px-5 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-slate-300">
              Rent<span className="gradient-text">Radar</span>
            </span>
            <span>· Built for Bangalore tenants</span>
          </div>
          <p>Data refreshed live on every search · Not affiliated with any listing portal</p>
        </div>
      </footer>
    </div>
  );
}
