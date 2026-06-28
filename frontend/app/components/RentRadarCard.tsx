"use client";

import { useMemo } from "react";
import ListingCards from "./ListingCards";
import LocalityScores from "./LocalityScores";

interface RentBrief {
  locality?: string;
  search_summary?: string;
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

const TREND_STYLES: Record<string, string> = {
  rising:  "text-red-400",
  falling: "text-emerald-400",
  stable:  "text-yellow-400",
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
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
        <span>{icon}</span>
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function RentRadarCard({ rawBrief }: Props) {
  const brief: RentBrief | null = useMemo(() => {
    try {
      // Strip markdown code fences if Claude wraps it
      const cleaned = rawBrief.replace(/^```json\s*/i, "").replace(/```\s*$/, "").trim();
      return JSON.parse(cleaned);
    } catch {
      return null;
    }
  }, [rawBrief]);

  // Fallback: show raw text if JSON parse failed
  if (!brief) {
    return (
      <div className="card-enter w-full max-w-2xl mx-auto mt-8 p-6 rounded-2xl bg-[#111118] border border-[#1e1e2e]">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Raw Response</p>
        <pre className="text-sm text-slate-300 whitespace-pre-wrap break-words">{rawBrief}</pre>
      </div>
    );
  }

  const trendStyle = TREND_STYLES[brief.price_trend?.toLowerCase() ?? "stable"] ?? "text-slate-400";

  return (
    <div className="card-enter w-full max-w-2xl mx-auto mt-8 rounded-2xl bg-[#111118] border border-[#1e1e2e] overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-[#1e1e2e] bg-[#0d0d15]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-indigo-400 font-semibold uppercase tracking-wider mb-1">
              Rent Radar · Live Brief
            </p>
            <h2 className="text-xl font-bold text-slate-100">
              {brief.locality ?? "Bangalore"}
            </h2>
            {brief.search_summary && (
              <p className="text-sm text-slate-400 mt-0.5">{brief.search_summary}</p>
            )}
          </div>
          {brief.price_trend && (
            <div className="text-right flex-shrink-0">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Trend</p>
              <p className={`text-lg font-bold uppercase ${trendStyle}`}>
                {brief.price_trend === "rising" ? "↑" : brief.price_trend === "falling" ? "↓" : "→"}{" "}
                {brief.price_trend}
              </p>
            </div>
          )}
        </div>
        {brief.trend_note && (
          <p className="text-xs text-slate-500 mt-2">{brief.trend_note}</p>
        )}
      </div>

      <div className="px-6 py-5 space-y-7 divide-y divide-[#1e1e2e]">
        {/* Top Listings */}
        {brief.top_listings?.length > 0 && (
          <Section title="Top Listings" icon="🏠">
            <ListingCards listings={brief.top_listings} />
          </Section>
        )}

        {/* Locality Scores */}
        {brief.locality_scores && Object.keys(brief.locality_scores).length > 0 && (
          <div className="pt-6">
            <Section title="Locality Scores" icon="📊">
              <LocalityScores scores={brief.locality_scores} />
            </Section>
          </div>
        )}

        {/* Reddit Pulse */}
        {brief.reddit_pulse && (
          <div className="pt-6">
            <Section title="Reddit Pulse" icon="📣">
              <p className="text-sm text-slate-300 leading-relaxed italic">
                "{brief.reddit_pulse}"
              </p>
            </Section>
          </div>
        )}

        {/* HN Signal */}
        {brief.hn_signal && (
          <div className="pt-6">
            <Section title="Tech Worker Signal (HN)" icon="💻">
              <p className="text-sm text-slate-300 leading-relaxed">{brief.hn_signal}</p>
            </Section>
          </div>
        )}

        {/* Green & Red Flags */}
        {((brief.green_flags?.length ?? 0) > 0 || (brief.red_flags?.length ?? 0) > 0) && (
          <div className="pt-6">
            <div className="grid grid-cols-2 gap-6">
              {brief.green_flags?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-emerald-500 uppercase tracking-widest mb-2">
                    ✅ Green Flags
                  </p>
                  <ul className="space-y-1">
                    {brief.green_flags.map((f, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-1.5">
                        <span className="text-emerald-500 mt-0.5">•</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.red_flags?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-red-500 uppercase tracking-widest mb-2">
                    🔴 Red Flags
                  </p>
                  <ul className="space-y-1">
                    {brief.red_flags.map((f, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-1.5">
                        <span className="text-red-500 mt-0.5">•</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scam Alerts */}
        {brief.scam_alerts?.length > 0 && (
          <div className="pt-6">
            <Section title="Scam Alerts" icon="⚠️">
              <div className="bg-amber-950/40 border border-amber-700/40 rounded-xl p-4 space-y-1.5">
                {brief.scam_alerts.map((a, i) => (
                  <p key={i} className="text-sm text-amber-300 flex items-start gap-2">
                    <span className="text-amber-500 flex-shrink-0">!</span>
                    {a}
                  </p>
                ))}
              </div>
            </Section>
          </div>
        )}

        {/* Verdict */}
        {brief.verdict && (
          <div className="pt-6">
            <Section title="Verdict" icon="🎯">
              <div className="bg-indigo-950/40 border border-indigo-700/30 rounded-xl p-4">
                <p className="text-sm text-slate-200 leading-relaxed">{brief.verdict}</p>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
