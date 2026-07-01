"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import SearchBar from "./components/SearchBar";
import SourceIndicators from "./components/SourceIndicators";
import RentRadarCard from "./components/RentRadarCard";
import HowItWorks from "./components/HowItWorks";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

const ALL_SOURCES = ["Reddit", "Google News", "Hacker News", "NoBroker", "OLX", "Housing.com"];

export default function Home() {
  const [loading, setLoading]         = useState(false);
  const [sources, setSources]         = useState<string[]>([]);
  const [statuses, setStatuses]       = useState<Record<string, SourceStatus>>({});
  const [brief, setBrief]             = useState<string | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [parsedQuery, setParsedQuery] = useState<Record<string, any> | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const abortRef                      = useRef<AbortController | null>(null);

  useEffect(() => { return () => { abortRef.current?.abort(); }; }, []);

  const handleSearch = useCallback(async (query: string) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true); setHasSearched(true);
    setBrief(null); setError(null); setParsedQuery(null);
    setSources([]); setStatuses({});

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      });

      if (!res.body) throw new Error("Response body is empty.");
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
              case "parsed":    setParsedQuery(event.data); break;
              case "fetching":
                setSources(event.sources ?? ALL_SOURCES);
                setStatuses(Object.fromEntries((event.sources ?? ALL_SOURCES).map((s: string) => [s, "fetching"])));
                break;
              case "source_complete":
                setStatuses((prev) => ({ ...prev, [event.source]: event.status === "ok" ? "ok" : "error" }));
                break;
              case "brief":  setBrief(event.data); break;
              case "done":   setLoading(false); break;
              case "error":  setError(event.message ?? "Something went wrong."); setLoading(false); break;
            }
          } catch { /* malformed SSE — ignore */ }
        }
      }
    } catch (err: any) {
      if (err?.name === "AbortError") { setError(null); }
      else { setError("Backend unreachable — please check the server is running and try again."); }
    } finally { setLoading(false); }
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col">

      {/* ── Navigation ────────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 border-b border-white/[0.06]"
        style={{ background: "rgba(6,6,15,0.88)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)" }}
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2.5">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-xl"
              style={{ background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 60%, #9333ea 100%)", boxShadow: "0 0 18px -4px rgba(99,102,241,0.7)" }}
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
              </svg>
            </span>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-[17px] font-bold tracking-tight text-white">
                Rent<span className="gradient-text">Radar</span>
              </span>
              <span className="hidden sm:inline rounded-full border border-indigo-500/25 bg-indigo-500/[0.07] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-indigo-400">
                Beta
              </span>
            </div>
          </a>

          {/* Nav right */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/[0.05] px-3 py-1.5 text-[11px] font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live · 6 sources
            </div>
            <a
              href="https://github.com/abdulrr25/RentRadar"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:border-white/[0.18] hover:text-white"
              style={{ background: "rgba(255,255,255,0.025)" }}
            >
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor">
                <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.4-3.9-1.4-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z" />
              </svg>
              GitHub
            </a>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* ── Hero ───────────────────────────────────────────────────────── */}
        <section className="mx-auto max-w-3xl px-4 sm:px-6 pt-12 sm:pt-20 md:pt-28 pb-10 text-center">
          {/* Badge */}
          <div className="rise inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/[0.06] px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-300">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            AI Rental Intelligence · Bangalore
          </div>

          {/* Heading */}
          <h1 className="rise delay-1 mt-6 font-display font-extrabold leading-[1.07] tracking-tight text-white text-4xl sm:text-5xl md:text-[3.75rem]">
            Find your flat.
            <br />
            <span className="gradient-text">Let AI do the work.</span>
          </h1>

          {/* Subheading */}
          <p className="rise delay-2 mx-auto mt-5 max-w-lg text-sm sm:text-[15px] leading-relaxed text-slate-400">
            Ask in plain English.{" "}
            <span className="text-slate-300">RentRadar</span> scans NoBroker, OLX,
            Housing.com, Reddit and news in parallel — then returns ranked listings,
            locality scores, price trends and scam alerts in one brief.
          </p>

          {/* Search */}
          <div className="rise delay-3 mt-9">
            <SearchBar onSearch={handleSearch} loading={loading} />
          </div>

          {/* Stats strip */}
          <div className="rise delay-4 mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[11px] text-slate-600">
            {[
              { val: "6",       label: "live data sources" },
              { val: "Llama 3.3", label: "70B synthesis" },
              { val: "<15s",    label: "avg response time" },
              { val: "Free",    label: "no account needed" },
            ].map(({ val, label }) => (
              <span key={label} className="flex items-center gap-1.5">
                <span className="font-semibold text-slate-400">{val}</span>
                <span>{label}</span>
              </span>
            ))}
          </div>
        </section>

        {/* ── Source indicators ──────────────────────────────────────────── */}
        {sources.length > 0 && (
          <section className="mx-auto max-w-2xl px-4 sm:px-6 mb-2 fade-in">
            <SourceIndicators sources={sources} statuses={statuses} />
            {parsedQuery && (
              <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
                {[
                  { icon: "📍", val: parsedQuery.locality },
                  { icon: "🛏", val: parsedQuery.bhk },
                  { icon: "💰", val: `max ₹${parsedQuery.max_rent?.toLocaleString("en-IN")}` },
                ].map(({ icon, val }) => (
                  <span key={val} className="glass rounded-full px-3.5 py-1 text-slate-300">
                    {icon} {val}
                  </span>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ── Error ─────────────────────────────────────────────────────── */}
        {error && (
          <section className="mx-auto mt-6 max-w-2xl px-4 sm:px-6">
            <div className="flex items-start gap-3 rounded-2xl border border-red-700/30 bg-red-950/20 px-5 py-4 text-sm text-red-300">
              <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          </section>
        )}

        {/* ── Results ───────────────────────────────────────────────────── */}
        <section className="mx-auto max-w-2xl px-4 sm:px-6 pb-24">
          {brief && <RentRadarCard rawBrief={brief} />}
          {loading && !brief && (
            <div className="mt-8 space-y-3">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="shimmer h-20 rounded-2xl border border-white/[0.06]"
                  style={{ background: "rgba(255,255,255,0.016)", opacity: 1 - i * 0.28 }}
                />
              ))}
            </div>
          )}
        </section>

        {!hasSearched && <HowItWorks />}
      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        className="border-t border-white/[0.06]"
        style={{ background: "rgba(6,6,15,0.7)" }}
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
          <div className="flex items-center gap-2.5">
            <span className="font-display text-sm font-bold text-slate-400">
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
