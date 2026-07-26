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

const SOURCE_STYLE: Record<
  string,
  { accent: string; badge: string; chipBg: string; chipText: string; initial: string }
> = {
  NoBroker: {
    accent: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
    badge: "border-green-200 bg-green-50 text-green-700",
    chipBg: "bg-green-600",
    chipText: "text-white",
    initial: "N",
  },
  OLX: {
    accent: "linear-gradient(135deg, #9333ea 0%, #7e22ce 100%)",
    badge: "border-purple-200 bg-purple-50 text-purple-700",
    chipBg: "bg-purple-600",
    chipText: "text-white",
    initial: "O",
  },
  "Housing.com": {
    accent: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
    badge: "border-blue-200 bg-blue-50 text-blue-700",
    chipBg: "bg-blue-600",
    chipText: "text-white",
    initial: "H",
  },
};
const DEFAULT_STYLE = {
  accent: "linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)",
  badge: "border-slate-200 bg-slate-50 text-slate-700",
  chipBg: "bg-slate-500",
  chipText: "text-white",
  initial: "?",
};

function CardContent({ l }: { l: Listing }) {
  const style = SOURCE_STYLE[l.source] ?? DEFAULT_STYLE;
  const clickable = Boolean(l.url);
  const isTopPick = l.rank === 1;

  return (
    <div className="min-w-0">
      {/* Source strip: logo chip + name, rank/best-match badge */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold ${style.chipText}`}
            style={{ background: style.accent }}
          >
            {style.initial}
          </span>
          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${style.badge}`}>
            {l.source}
          </span>
        </div>
        {isTopPick ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-700">
            <svg viewBox="0 0 24 24" className="h-3 w-3" fill="currentColor">
              <path d="M12 2l2.9 6.6 7.1.6-5.4 4.7 1.7 7-6.3-3.8-6.3 3.8 1.7-7-5.4-4.7 7.1-.6z" />
            </svg>
            Best Match
          </span>
        ) : (
          <span className="text-[11px] font-medium text-slate-400">#{l.rank}</span>
        )}
      </div>

      {/* Title + Rent */}
      <div className="mt-3 flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <div className="min-w-0">
          <p className="line-clamp-2 font-display font-semibold text-slate-900 leading-snug">{l.locality_detail}</p>
          <p className="mt-0.5 text-xs text-slate-500">{l.bhk}</p>
        </div>
        <div className="flex-shrink-0 text-right">
          {l.rent != null ? (
            <div className="rounded-lg bg-emerald-50 px-2.5 py-1.5">
              <p className="font-display text-lg font-bold leading-none text-emerald-700">
                ₹{l.rent.toLocaleString("en-IN")}
              </p>
              <p className="mt-0.5 text-[10px] font-medium text-emerald-600">per month</p>
            </div>
          ) : (
            <div className="rounded-lg bg-slate-100 px-2.5 py-1.5">
              <p className="text-sm font-semibold text-slate-600">See listing</p>
              <p className="mt-0.5 text-[10px] text-slate-500">for price</p>
            </div>
          )}
        </div>
      </div>

      {/* Commute */}
      {l.commute_note && (
        <p className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-500">
          <svg viewBox="0 0 24 24" className="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
          </svg>
          {l.commute_note}
        </p>
      )}

      {/* Highlights */}
      {l.highlights && l.highlights.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {l.highlights.map((h) => (
            <span key={h} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">
              {h}
            </span>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="mt-3.5 flex items-center justify-between border-t border-slate-100 pt-3">
        <span className="text-[11px] text-slate-400">Verified link to the exact listing</span>
        {clickable && (
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold text-white shadow-sm transition group-hover:brightness-110"
            style={{ background: style.accent }}
          >
            View listing
            <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </span>
        )}
      </div>
    </div>
  );
}

export default function ListingCards({ listings }: { listings: Listing[] }) {
  if (!listings?.length) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {listings.map((l) => {
        const base =
          "group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lift";
        const shadow = { boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)" };

        return l.url ? (
          <a key={l.rank} href={l.url} target="_blank" rel="noopener noreferrer" title={`View on ${l.source}`} className={base} style={shadow}>
            <CardContent l={l} />
          </a>
        ) : (
          <div key={l.rank} className={base} style={shadow}>
            <CardContent l={l} />
          </div>
        );
      })}
    </div>
  );
}
