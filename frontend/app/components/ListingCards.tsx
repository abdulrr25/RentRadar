"use client";

interface Listing {
  rank: number;
  locality_detail: string;
  rent: number | null;
  bhk: string;
  source: string;
  commute_note?: string;
  highlights?: string[];
  url?: string | null;
}

const SOURCE_STYLE: Record<string, { stripe: string; badge: string; dot: string }> = {
  NoBroker:      { stripe: "#16a34a", badge: "border-green-300 bg-green-100 text-green-800",   dot: "bg-green-600"  },
  OLX:           { stripe: "#9333ea", badge: "border-purple-300 bg-purple-100 text-purple-800", dot: "bg-purple-600" },
  "Housing.com": { stripe: "#2563eb", badge: "border-blue-300 bg-blue-100 text-blue-800",       dot: "bg-blue-600"   },
};
const DEFAULT_STYLE = { stripe: "#4f46e5", badge: "border-slate-300 bg-slate-100 text-slate-700", dot: "bg-slate-500" };

function CardContent({ l }: { l: Listing }) {
  const style  = SOURCE_STYLE[l.source] ?? DEFAULT_STYLE;
  const clickable = Boolean(l.url);

  return (
    <div className="flex gap-3 items-start min-w-0">
      {/* Rank */}
      <div className="flex-shrink-0 flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-100 text-xs font-bold text-indigo-700">
        {l.rank}
      </div>

      <div className="min-w-0 flex-1">
        {/* Title + Rent row */}
        <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
          <div className="min-w-0">
            <p className="line-clamp-2 sm:truncate font-semibold text-slate-900 leading-snug">{l.locality_detail}</p>
            <p className="mt-0.5 text-xs text-slate-500">{l.bhk}</p>
          </div>
          <div className="flex-shrink-0 text-right">
            {l.rent != null ? (
              <>
                <p className="font-display text-lg font-bold text-emerald-600 leading-none">₹{l.rent.toLocaleString("en-IN")}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">per month</p>
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-slate-600">See listing</p>
                <p className="text-[11px] text-slate-500 mt-0.5">for price</p>
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
              <span key={h} className="rounded-md border border-slate-300 bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{h}</span>
            ))}
          </div>
        )}

        {/* Footer: source badge + link */}
        <div className="mt-3 flex items-center justify-between gap-2">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${style.badge}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            {l.source}
          </span>
          {clickable && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-brand-600 transition group-hover:text-brand-700">
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
        const base  = "group relative overflow-hidden rounded-xl border border-slate-300 bg-white transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lift";

        const body = (
          <>
            <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl" style={{ background: style.stripe }} />
            <div className="pl-4 pr-4 py-4"><CardContent l={l} /></div>
          </>
        );

        return l.url ? (
          <a key={l.rank} href={l.url} target="_blank" rel="noopener noreferrer" title={`View on ${l.source}`} className={base}
            style={{ boxShadow: "0 1px 3px rgba(15,23,42,0.06)" }}>
            {body}
          </a>
        ) : (
          <div key={l.rank} className={base} style={{ boxShadow: "0 1px 3px rgba(15,23,42,0.06)" }}>
            {body}
          </div>
        );
      })}
    </div>
  );
}
