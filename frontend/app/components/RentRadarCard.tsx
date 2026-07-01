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

interface Props { rawBrief: string; }

const TREND_META: Record<string, { color: string; arrow: string; bg: string; border: string }> = {
  rising:  { color: "text-red-300",     arrow: "↑", bg: "bg-red-500/[0.07]",    border: "border-red-700/25" },
  falling: { color: "text-emerald-300", arrow: "↓", bg: "bg-emerald-500/[0.07]", border: "border-emerald-700/25" },
  stable:  { color: "text-amber-300",   arrow: "→", bg: "bg-amber-500/[0.07]",   border: "border-amber-700/25" },
};

/* Minimal SVG icons — matches Lucide Feather style */
function Icon({ d, size = "h-3.5 w-3.5" }: { d: string; size?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-3.5">
      <h3 className="flex items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        <span className="text-slate-500">{icon}</span>
        {title}
      </h3>
      {children}
    </div>
  );
}

function Divider() {
  return <div className="border-t border-white/[0.055]" />;
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
    } catch { return null; }
  }, [rawBrief]);

  /* Sources down */
  if (brief?.sources_unavailable) {
    return (
      <div className="card-enter mt-8 w-full rounded-2xl border border-amber-700/30 p-6" style={{ background: "rgba(120,60,0,0.08)" }}>
        <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-300">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          Data sources unavailable
        </p>
        <p className="text-sm leading-relaxed text-amber-200/80">
          {brief.message ?? "All live data sources are currently unavailable. Please try again shortly."}
        </p>
      </div>
    );
  }

  /* Malformed JSON fallback */
  if (!brief) {
    return (
      <div className="card-enter mt-8 w-full rounded-2xl border border-white/[0.07] p-6" style={{ background: "rgba(255,255,255,0.02)" }}>
        <p className="mb-3 text-[10px] uppercase tracking-wider text-slate-500">Raw response</p>
        <pre className="whitespace-pre-wrap break-words text-sm text-slate-400">{rawBrief}</pre>
      </div>
    );
  }

  const trendKey = brief.price_trend?.toLowerCase() ?? "stable";
  const trend = TREND_META[trendKey] ?? TREND_META.stable;

  return (
    <div className="card-enter card-surface mt-8 w-full overflow-hidden rounded-3xl">

      {/* ── Card header ──────────────────────────────────────────────────── */}
      <div className="relative px-5 sm:px-7 py-6" style={{ background: "linear-gradient(160deg, rgba(99,102,241,0.07) 0%, transparent 60%)" }}>
        {/* Top accent line */}
        <div className="absolute top-0 left-0 right-0 h-[1.5px]" style={{ background: "linear-gradient(90deg, transparent 0%, rgba(99,102,241,0.6) 40%, rgba(139,92,246,0.4) 70%, transparent 100%)" }} />

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400/80">
              <span className="h-1 w-1 rounded-full bg-indigo-400" />
              Live Brief
            </p>
            <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {brief.locality ?? "Bangalore"}
            </h2>
            {brief.search_summary && (
              <p className="mt-1.5 text-sm text-slate-400 leading-relaxed">{brief.search_summary}</p>
            )}
          </div>

          {brief.price_trend && (
            <div className={`flex-shrink-0 rounded-xl border px-3.5 py-2.5 text-right ${trend.bg} ${trend.border}`}>
              <p className="text-[9px] font-medium uppercase tracking-widest text-slate-500 mb-0.5">Trend</p>
              <p className={`font-display text-lg font-bold ${trend.color}`}>
                {trend.arrow} {brief.price_trend}
              </p>
            </div>
          )}
        </div>

        {brief.trend_note && (
          <p className="mt-3 text-xs leading-relaxed text-slate-500">{brief.trend_note}</p>
        )}
      </div>

      {/* ── Card body ────────────────────────────────────────────────────── */}
      <div className="space-y-0 divide-y divide-white/[0.055]">

        {/* Budget note */}
        {brief.budget_note && (
          <div className="px-5 sm:px-7 py-5">
            <div className="flex items-start gap-3 rounded-xl border border-amber-700/30 bg-amber-500/[0.06] p-4 text-sm text-amber-200/90">
              <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {brief.budget_note}
            </div>
          </div>
        )}

        {/* Top listings */}
        {brief.top_listings && brief.top_listings.length > 0 && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Top Listings"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
              }
            >
              <ListingCards listings={brief.top_listings} />
            </Section>
          </div>
        )}

        {/* Locality scores */}
        {brief.locality_scores && Object.keys(brief.locality_scores).length > 0 && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Locality Scores"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
                </svg>
              }
            >
              <LocalityScores scores={brief.locality_scores} />
              <p className="mt-3 text-[10.5px] leading-relaxed text-slate-600">
                Estimates from Reddit, HN &amp; news — not objective data. Online discussions
                skew toward tech workers and popular neighbourhoods. Use as a signal, not ground truth.
              </p>
            </Section>
          </div>
        )}

        {/* Reddit pulse */}
        {brief.reddit_pulse && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Reddit Pulse"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              }
            >
              <blockquote
                className="rounded-xl border-l-2 border-indigo-500/40 pl-4 pr-4 py-3 text-sm italic leading-relaxed text-slate-300"
                style={{ background: "rgba(99,102,241,0.04)" }}
              >
                {brief.reddit_pulse}
              </blockquote>
            </Section>
          </div>
        )}

        {/* HN signal */}
        {brief.hn_signal && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Tech Worker Signal (HN)"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
                </svg>
              }
            >
              <p className="text-sm leading-relaxed text-slate-300">{brief.hn_signal}</p>
            </Section>
          </div>
        )}

        {/* Green + Red flags */}
        {(brief.green_flags?.length || brief.red_flags?.length) ? (
          <div className="px-5 sm:px-7 py-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {brief.green_flags && brief.green_flags.length > 0 && (
                <div className="rounded-xl border border-emerald-700/20 p-4" style={{ background: "rgba(16,185,129,0.04)" }}>
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-400">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    Green Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.green_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-emerald-400" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.red_flags && brief.red_flags.length > 0 && (
                <div className="rounded-xl border border-red-700/20 p-4" style={{ background: "rgba(239,68,68,0.04)" }}>
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-400">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    Red Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.red_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-red-400" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ) : null}

        {/* Scam alerts */}
        {brief.scam_alerts && brief.scam_alerts.length > 0 && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Scam Alerts"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              }
            >
              <div className="space-y-2.5 rounded-xl border border-amber-700/30 p-4" style={{ background: "rgba(120,53,15,0.08)" }}>
                {brief.scam_alerts.map((a, i) => (
                  <p key={i} className="flex items-start gap-2.5 text-sm text-amber-200/90">
                    <span className="mt-0.5 flex-shrink-0 text-amber-500 font-bold">!</span>
                    {a}
                  </p>
                ))}
              </div>
            </Section>
          </div>
        )}

        {/* Verdict */}
        {brief.verdict && (
          <div className="px-5 sm:px-7 py-6">
            <Section
              title="Verdict"
              icon={
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
                </svg>
              }
            >
              <div
                className="rounded-xl border border-indigo-500/20 p-5"
                style={{ background: "linear-gradient(160deg, rgba(99,102,241,0.07) 0%, rgba(99,102,241,0.02) 100%)" }}
              >
                <p className="text-sm leading-[1.75] text-slate-200">{brief.verdict}</p>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
