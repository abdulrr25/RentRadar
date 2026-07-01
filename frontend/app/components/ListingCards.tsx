"use client";

interface Listing {
  rank: number;
  locality_detail: string;
  rent: number;
  bhk: string;
  source: string;
  commute_note?: string;
  highlights?: string[];
  url?: string | null;
}

/* Left border colour + source badge per platform */
const SOURCE_STYLE: Record<string, { stripe: string; badge: string; dot: string }> = {
  NoBroker:      { stripe: "#22c55e", badge: "border-green-600/25 bg-green-500/[0.07] text-green-300",   dot: "bg-green-400"  },
  OLX:           { stripe: "#a855f7", badge: "border-purple-600/25 bg-purple-500/[0.07] text-purple-300", dot: "bg-purple-400" },
  "Housing.com": { stripe: "#3b82f6", badge: "border-blue-600/25 bg-blue-500/[0.07] text-blue-300",      dot: "bg-blue-400"   },
};

const DEFAULT_STYLE = { stripe: "#6366f1", badge: "border-slate-700/40 bg-slate-800/40 text-slate-400", dot: "bg-slate-400" };

function CardContent({ l }: { l: Listing }) {
  const style = SOURCE_STYLE[l.source] ?? DEFAULT_STYLE;
  const clickable = Boolean(l.url);

  return (
    <div className="flex gap-4 items-start min-w-0">
      {/* Rank */}
      <div
        className="flex-shrink-0 flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold text-indigo-300"
        style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.18)" }}
      >
        {l.rank}
      </div>

      {/* Main content */}
      <div className="min-w-0 flex-1">
        {/* Title row */}
        <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
          <div className="min-w-0">
            <p className="line-clamp-2 sm:truncate font-semibold text-slate-100 leading-snug">{l.locality_detail}</p>
            <p className="mt-0.5 text-xs text-slate-500">{l.bhk}</p>
          </div>
          {/* Rent */}
          <div className="flex-shrink-0 text-right">
            {l.rent != null ? (
              <>
                <p className="font-display text-xl font-bold text-emerald-400 leading-none">
                  ₹{l.rent.toLocaleString("en-IN")}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">per month</p>
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-slate-400">See listing</p>
                <p className="text-[11px] text-slate-600 mt-0.5">for price</p>
              </>
            )}
          </div>
        </div>

        {/* Commute */}
        {l.commute_note && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
            <svg viewBox="0 0 24 24" className="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            {l.commute_note}
          </p>
        )}

        {/* Highlights */}
        {l.highlights && l.highlights.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {l.highlights.map((h) => (
              <span
                key={h}
                className="rounded-md px-2 py-0.5 text-[11px] text-slate-400"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}
              >
                {h}
              </span>
            ))}
          </div>
        )}

        {/* Footer row: source badge + link */}
        <div className="mt-3 flex items-center justify-between gap-2">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${style.badge}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            {l.source}
          </span>
          {clickable && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-indigo-400 transition group-hover:text-indigo-300">
              View listing
              <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ListingCards({ listings }: { listings: Listing[] }) {
  if (!listings?.length) return null;

  return (
    <div className="space-y-2.5">
      {listings.map((l) => {
        const style = SOURCE_STYLE[l.source] ?? DEFAULT_STYLE;
        const cls = "group relative overflow-hidden rounded-xl transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_32px_-8px_rgba(0,0,0,0.6)]";
        const inner = (
          <div
            className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl flex-shrink-0"
            style={{ background: style.stripe }}
          />
        );
        const body = (
          <>
            {inner}
            <div className="pl-4 pr-4 py-4">
              <CardContent l={l} />
            </div>
          </>
        );
        const surfaceStyle = { background: "rgba(255,255,255,0.022)", border: "1px solid rgba(255,255,255,0.07)" };

        return l.url ? (
          <a
            key={l.rank}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            title={`View on ${l.source}`}
            className={cls}
            style={surfaceStyle}
          >
            {body}
          </a>
        ) : (
          <div key={l.rank} className={cls} style={surfaceStyle}>
            {body}
          </div>
        );
      })}
    </div>
  );
}
