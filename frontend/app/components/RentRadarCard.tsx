"use client";

import { useMemo } from "react";
import ListingCards from "./ListingCards";
import LocalityScores from "./LocalityScores";
import AlertSignup from "./AlertSignup";
import ShareButton from "./ShareButton";

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
  hn_signal?: string;
  green_flags?: string[];
  red_flags?: string[];
  scam_alerts?: string[];
  verdict?: string;
}

interface Props {
  rawBrief: string;
  parsedQuery?: { locality?: string; bhk?: string; max_rent?: number } | null;
  shareId?: string | null;
}

const TREND: Record<string, { color: string; bg: string; border: string; arrow: string }> = {
  rising:  { color: "text-red-600",     bg: "bg-red-50",     border: "border-red-200",     arrow: "↑" },
  falling: { color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", arrow: "↓" },
  stable:  { color: "text-amber-600",   bg: "bg-amber-50",   border: "border-amber-200",   arrow: "→" },
};

function SectionHeading({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <h3 className="flex items-center gap-2 text-[10.5px] font-bold uppercase tracking-[0.18em] text-slate-600 mb-4">
      <span className="text-slate-500">{icon}</span>
      {title}
    </h3>
  );
}

function Divider() {
  return <div className="border-t border-slate-200 mx-5 sm:mx-7" />;
}

export default function RentRadarCard({ rawBrief, parsedQuery, shareId }: Props) {
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
    <div className="card-enter ring-gradient card mt-8 w-full overflow-hidden rounded-3xl" style={{ boxShadow: "0 24px 64px -12px rgba(79,70,229,0.22), 0 8px 24px -4px rgba(15,23,42,0.1)" }}>

      {/* Header */}
      <div className="relative px-5 sm:px-7 py-8 overflow-hidden" style={{ background: "linear-gradient(135deg, #312e81 0%, #4338ca 55%, #6d28d9 100%)" }}>
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full opacity-30" style={{ background: "radial-gradient(circle, #a78bfa 0%, transparent 70%)", filter: "blur(30px)" }} />
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-200">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-300 animate-pulse" />
              Live Brief · RentRadar
            </p>
            <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {brief.locality ?? "Bangalore"}
            </h2>
            {brief.search_summary && (
              <p className="mt-1.5 text-sm text-indigo-100 leading-relaxed">{brief.search_summary}</p>
            )}
          </div>
          {brief.price_trend && (
            <div className="flex-shrink-0 rounded-xl border border-white/20 bg-white/10 px-3.5 py-2.5 text-right backdrop-blur-sm">
              <p className="text-[9px] font-semibold uppercase tracking-widest text-indigo-200 mb-0.5">Trend</p>
              <p className={`font-display text-lg font-bold text-white`}>{trend.arrow} {brief.price_trend}</p>
            </div>
          )}
        </div>
        {brief.trend_note && <p className="mt-3 text-xs text-indigo-200 leading-relaxed">{brief.trend_note}</p>}
        {shareId && parsedQuery?.locality && parsedQuery?.bhk && parsedQuery?.max_rent && (
          <div className="mt-4 flex justify-end">
            <ShareButton shareId={shareId} locality={parsedQuery.locality} bhk={parsedQuery.bhk} maxRent={parsedQuery.max_rent} />
          </div>
        )}
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

      {/* Alert signup — shown regardless of whether this search found an
          in-budget listing, since "nothing matched yet" is exactly when a
          user most wants to be notified the moment something does. */}
      {parsedQuery?.locality && parsedQuery?.bhk && parsedQuery?.max_rent && (
        <>
          <div className="px-5 sm:px-7 py-6">
            <AlertSignup locality={parsedQuery.locality} bhk={parsedQuery.bhk} maxRent={parsedQuery.max_rent} />
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
            <p className="mt-4 text-[11px] text-slate-500 leading-relaxed">
              Estimates from HN &amp; news — not objective data. Online discussions skew toward tech workers and popular neighbourhoods.
            </p>
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
            <p className="text-sm leading-relaxed text-slate-700">{brief.hn_signal}</p>
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
                <div className="rounded-xl border border-emerald-300 bg-emerald-100 p-4">
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-800">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    Green Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.green_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-emerald-900">
                        <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-emerald-600" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.red_flags && brief.red_flags.length > 0 && (
                <div className="rounded-xl border border-red-300 bg-red-100 p-4">
                  <p className="mb-3 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-800">
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    Red Flags
                  </p>
                  <ul className="space-y-2">
                    {brief.red_flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-red-900">
                        <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-red-600" />{f}
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
          <div className="rounded-xl border border-slate-200 border-l-4 border-l-brand-500 bg-slate-50 p-5">
            <p className="text-sm leading-[1.75] text-slate-800">{brief.verdict}</p>
          </div>
        </div>
      )}
    </div>
  );
}
