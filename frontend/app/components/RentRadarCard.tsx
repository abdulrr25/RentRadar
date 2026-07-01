"use client";

import { useMemo } from "react";
import ListingCards from "./ListingCards";
import LocalityScores from "./LocalityScores";

interface RentBrief {
  locality?: string;
  search_summary?: string;
  sources_unavailable?: boolean;
  message?: string;
  budget_note?: string;
  top_listings?: any[];
  locality_scores?: Record<string, number>;
  price_trend?: string;
  trend_note?: string;
  reddit_pulse?: string;
  hn_signal?: string;
  green_flags?: string[];
  red_flags?: string[];
  scam_alerts?: string[];
  verdict?: string;
}

interface Props {
  rawBrief: string;
}

const TREND_META: Record<string, { color: string; arrow: string; bg: string }> = {
  rising:  { color: "text-red-400",     arrow: "↑", bg: "bg-red-500/10 border-red-700/30" },
  falling: { color: "text-emerald-400", arrow: "↓", bg: "bg-emerald-500/10 border-emerald-700/30" },
  stable:  { color: "text-amber-400",   arrow: "→", bg: "bg-amber-500/10 border-amber-700/30" },
};

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        <span className="text-sm">{icon}</span>
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function RentRadarCard({ rawBrief }: Props) {
  const brief: RentBrief | null = useMemo(() => {
    try {
      const stripped = rawBrief.replace(/^```json\s*/i, "").replace(/```\s*$/m, "").trim();
      const parsed = JSON.parse(stripped);
      if (parsed?.error === "synthesis_failed" && parsed?.raw) {
        const inner = parsed.raw.replace(/^```json\s*/i, "").replace(/```\s*$/m, "").trim();
        return JSON.parse(inner);
      }
      return parsed;
    } catch {
      return null;
    }
  }, [rawBrief]);

  // Sources down (e.g. API quota exhausted) — honest message
  if (brief?.sources_unavailable) {
    return (
      <div className="card-enter mx-auto mt-8 w-full max-w-2xl rounded-2xl border border-amber-700/40 bg-amber-950/25 p-6">
        <p className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-amber-300">
          <span>⚠️</span> Data sources unavailable
        </p>
        <p className="text-sm leading-relaxed text-amber-200/90">
          {brief.message ??
            "All live data sources are currently unavailable. Please try again shortly."}
        </p>
      </div>
    );
  }

  // Fallback: raw text if JSON parse failed
  if (!brief) {
    return (
      <div className="card-enter mx-auto mt-8 w-full max-w-2xl rounded-2xl glass p-6">
        <p className="mb-3 text-xs uppercase tracking-wider text-slate-500">Raw response</p>
        <pre className="whitespace-pre-wrap break-words text-sm text-slate-300">{rawBrief}</pre>
      </div>
    );
  }

  const trendKey = brief.price_trend?.toLowerCase() ?? "stable";
  const trend = TREND_META[trendKey] ?? TREND_META.stable;

  return (
    <div className="card-enter mx-auto mt-8 w-full max-w-2xl overflow-hidden rounded-3xl border border-white/[0.08] bg-white/[0.025] shadow-lift backdrop-blur-xl">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="relative border-b border-white/[0.06] px-4 sm:px-6 py-5 sm:py-6">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-indigo-500/[0.08] via-transparent to-transparent" />
        <div className="relative flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-1.5 inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-indigo-300/90">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
              Rent Radar · Live Brief
            </p>
            <h2 className="font-display text-2xl font-bold tracking-tight text-white">
              {brief.locality ?? "Bangalore"}
            </h2>
            {brief.search_summary && (
              <p className="mt-1 text-sm text-slate-400">{brief.search_summary}</p>
            )}
          </div>

          {brief.price_trend && (
            <div className={`flex-shrink-0 rounded-xl border px-3 py-2 text-right ${trend.bg}`}>
              <p className="text-[10px] uppercase tracking-wider text-slate-400">Trend</p>
              <p className={`font-display text-base font-bold uppercase ${trend.color}`}>
                {trend.arrow} {brief.price_trend}
              </p>
            </div>
          )}
        </div>
        {brief.trend_note && (
          <p className="relative mt-3 text-xs text-slate-500">{brief.trend_note}</p>
        )}
      </div>

      {/* ── Body ────────────────────────────────────────────────────── */}
      <div className="space-y-6 sm:space-y-7 px-4 sm:px-6 py-5 sm:py-6">
        {brief.budget_note && (
          <div className="flex items-start gap-2 rounded-xl border border-amber-700/40 bg-amber-950/30 p-3 text-sm text-amber-300">
            <span className="flex-shrink-0">💸</span>
            {brief.budget_note}
          </div>
        )}

        {brief.top_listings && brief.top_listings.length > 0 && (
          <Section title="Top Listings" icon="🏠">
            <ListingCards listings={brief.top_listings} />
          </Section>
        )}

        {brief.locality_scores && Object.keys(brief.locality_scores).length > 0 && (
          <div className="border-t border-white/[0.06] pt-7">
            <Section title="Locality Scores" icon="📊">
              <LocalityScores scores={brief.locality_scores} />
              <p className="mt-3 text-[11px] leading-relaxed text-slate-600">
                Sentiment estimates from Reddit, HN &amp; news — not objective data. Online discussions skew toward tech workers and popular neighbourhoods. Use as a signal, not ground truth.
              </p>
            </Section>
          </div>
        )}

        {brief.reddit_pulse && (
          <div className="border-t border-white/[0.06] pt-7">
            <Section title="Reddit Pulse" icon="📣">
              <blockquote className="rounded-xl border-l-2 border-indigo-500/50 bg-white/[0.02] px-4 py-3 text-sm italic leading-relaxed text-slate-300">
                {brief.reddit_pulse}
              </blockquote>
            </Section>
          </div>
        )}

        {brief.hn_signal && (
          <div className="border-t border-white/[0.06] pt-7">
            <Section title="Tech Worker Signal (HN)" icon="💻">
              <p className="text-sm leading-relaxed text-slate-300">{brief.hn_signal}</p>
            </Section>
          </div>
        )}

        {(brief.green_flags?.length || brief.red_flags?.length) ? (
          <div className="grid grid-cols-1 gap-5 border-t border-white/[0.06] pt-7 sm:grid-cols-2">
            {brief.green_flags && brief.green_flags.length > 0 && (
              <div className="rounded-xl border border-emerald-700/25 bg-emerald-500/[0.04] p-4">
                <p className="mb-2.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-emerald-400">
                  ✅ Green Flags
                </p>
                <ul className="space-y-1.5">
                  {brief.green_flags.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="mt-0.5 text-emerald-500">+</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {brief.red_flags && brief.red_flags.length > 0 && (
              <div className="rounded-xl border border-red-700/25 bg-red-500/[0.04] p-4">
                <p className="mb-2.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-red-400">
                  🔴 Red Flags
                </p>
                <ul className="space-y-1.5">
                  {brief.red_flags.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="mt-0.5 text-red-500">!</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}

        {brief.scam_alerts && brief.scam_alerts.length > 0 && (
          <div className="border-t border-white/[0.06] pt-7">
            <Section title="Scam Alerts" icon="⚠️">
              <div className="space-y-2 rounded-xl border border-amber-700/40 bg-amber-950/30 p-4">
                {brief.scam_alerts.map((a, i) => (
                  <p key={i} className="flex items-start gap-2 text-sm text-amber-300">
                    <span className="flex-shrink-0 font-bold text-amber-500">!</span>
                    {a}
                  </p>
                ))}
              </div>
            </Section>
          </div>
        )}

        {brief.verdict && (
          <div className="border-t border-white/[0.06] pt-7">
            <Section title="Verdict" icon="🎯">
              <div className="gradient-border rounded-xl bg-indigo-500/[0.06] p-4">
                <p className="text-sm leading-relaxed text-slate-200">{brief.verdict}</p>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
