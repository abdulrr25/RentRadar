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

const TREND: Record<string, { color: string; bg: string; border: string; arrow: string }> = {
  rising:  { color: "text-red-600",     bg: "bg-red-50",     border: "border-red-200",     arrow: "↑" },
  falling: { color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", arrow: "↓" },
  stable:  { color: "text-amber-600",   bg: "bg-amber-50",   border: "border-amber-200",   arrow: "→" },
};

function SectionHeading({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <h3 className="flex items-center gap-2 text-[10.5px] font-bold uppercase tracking-[0.18em] text-slate-400 mb-4">
      <span className="text-slate-400">{icon}</span>
      {title}
    </h3>
  );
}

function Divider() {
  return <div className="border-t border-slate-100 mx-5 sm:mx-7" />;
}

export default function RentRadarCard({ rawBrief }: Props) {
  const brief: RentBrief | null = useMemo(() => {
    try {
      const s = rawBrief.replace(/^```json\s*/i, "").replace(/```\s*$/m, "").trim();
      const p = JSON.parse(s);
      if (p?.error === "synthesis_failed" && p?.raw) return JSON.parse(p.raw.replace(/^```json\s*/i, "").replace(/```\s*$/m, "").trim());
      return p;
    } catch { return null; }
  }, [rawBrief]);

  if (brief?.sources_unavailable) {
    return (
      <div className="card-enter mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-800">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          Data sources temporarily unavailable
        </p>
        <p className="text-sm text-amber-700">{brief.message ?? "Please try again shortly."}</p>
      </div>
    );
  }

  if (!brief) {
    return (
      <div className="card-enter mt-8 rounded-2xl border border-slate-200 bg-white p-6">
        <p className="mb-3 text-[10px] uppercase tracking-wider text-slate-400">Raw response</p>
        <pre className="whitespace-pre-wrap break-words text-sm text-slate-600">{rawBrief}</pre>
      </div>
    );
  }

  const tKey = brief.price_trend?.toLowerCase() ?? "stable";
  const trend = TREND[tKey] ?? TREND.stable;

  return (
    <div className="card-enter card mt-8 w-full overflow-hidden rounded-3xl">

      {/* Header */}
      <div className="px-5 sm:px-7 py-6 bg-gradient-to-br from-brand-50 to-white border-b border-slate-100">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse" />
              Live Brief · RentRadar
            </p>
            <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              {brief.locality ?? "Bangalore"}
            </h2>
            {brief.search_summary && (
              <p className="mt-1.5 text-sm text-slate-500 leading-relaxed">{brief.search_summary}</p>
            )}
          </div>
          {brief.price_trend && (
            <div className={`flex-shrink-0 rounded-xl border px-3.5 py-2.5 text-right ${trend.bg} ${trend.border}`}>
              <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400 mb-0.5">Trend</p>
              <p className={`font-display text-lg font-bold ${trend.color}`}>{trend.arrow} {brief.price_trend}</p>
            </div>
          )}
        </div>
        {brief.trend_note && <p className="mt-3 text-xs text-slate-400 leading-relaxed">{brief.trend_note}</p>}
      </div>

      {/* Budget note */}
      {brief.budget_note && (
        <>
          <div className="px-5 sm:px-7 py-5">
            <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {brief.budget_note}
            </div>
          </div>
          <Divider />
        </>
      )}

      {/* Listings */}
      {brief.top_listings && brief.top_listings.length > 0 && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <SectionHeading title="Top Listings" icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            } />
            <ListingCards listings={brief.top_listings} />
          </div>
          <Divider />
        </>
      )}

      {/* Scores */}
      {brief.locality_scores && Object.keys(brief.locality_scores).length > 0 && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <SectionHeading title="Locality Scores" icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            } />
            <LocalityScores scores={brief.locality_scores} />
            <p className="mt-4 text-[11px] text-slate-400 leading-relaxed">
              Estimates from Reddit, HN &amp; news — not objective data. Online discussions skew toward tech workers and popular neighbourhoods.
            </p>
          </div>
          <Divider />
        </>
      )}

      {/* Reddit pulse */}
      {brief.reddit_pulse && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <SectionHeading title="Reddit Pulse" icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            } />
            <blockquote className="rounded-xl border-l-2 border-brand-300 bg-brand-50 pl-4 pr-4 py-3 text-sm italic leading-relaxed text-slate-700">
              {brief.reddit_pulse}
            </blockquote>
          </div>
          <Divider />
        </>
      )}

      {/* HN signal */}
      {brief.hn_signal && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <SectionHeading title="Tech Worker Signal (HN)" icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
            } />
            <p className="text-sm leading-relaxed text-slate-600">{brief.hn_signal}</p>
          </div>
          <Divider />
        </>
      )}

      {/* Green + Red flags */}
      {(brief.green_flags?.length || brief.red_flags?.length) ? (
        <>
          <div className="px-5 sm:px-7 py-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {brief.green_flags && brief.green_flags.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-700">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    Green Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.green_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-emerald-800">
                        <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-emerald-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.red_flags && brief.red_flags.length > 0 && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-700">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    Red Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.red_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-red-800">
                        <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-red-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
          <Divider />
        </>
      ) : null}

      {/* Scam alerts */}
      {brief.scam_alerts && brief.scam_alerts.length > 0 && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <SectionHeading title="Scam Alerts" icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            } />
            <div className="space-y-2.5 rounded-xl border border-amber-200 bg-amber-50 p-4">
              {brief.scam_alerts.map((a, i) => (
                <p key={i} className="flex items-start gap-2.5 text-sm text-amber-800">
                  <span className="mt-0.5 flex-shrink-0 font-bold text-amber-600">!</span>{a}
                </p>
              ))}
            </div>
          </div>
          <Divider />
        </>
      )}

      {/* Verdict */}
      {brief.verdict && (
        <div className="px-5 sm:px-7 py-6">
          <SectionHeading title="Verdict" icon={
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
            </svg>
          } />
          <div className="rounded-xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-5">
            <p className="text-sm leading-[1.75] text-slate-700">{brief.verdict}</p>
          </div>
        </div>
      )}
    </div>
  );
}
