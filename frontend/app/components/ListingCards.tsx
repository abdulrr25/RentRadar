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

const SOURCE_BADGE: Record<string, string> = {
  NoBroker: "bg-green-900/60 text-green-400 border-green-700/40",
  OLX: "bg-purple-900/60 text-purple-400 border-purple-700/40",
  "Housing.com": "bg-blue-900/60 text-blue-400 border-blue-700/40",
};

function ListingBody({ l }: { l: Listing }) {
  const clickable = Boolean(l.url);
  return (
    <>
      {/* Rank badge */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-900/50 border border-indigo-700/40 flex items-center justify-center text-indigo-300 font-bold text-sm">
        {l.rank}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <p className="font-semibold text-slate-100">{l.locality_detail}</p>
            {l.commute_note && (
              <p className="text-xs text-slate-500 mt-0.5">{l.commute_note}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-lg font-bold text-emerald-400">
              ₹{l.rent.toLocaleString("en-IN")}
              <span className="text-sm font-normal text-slate-500">/mo</span>
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border font-medium inline-flex items-center gap-1 ${
                SOURCE_BADGE[l.source] ?? "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {l.source}
              {clickable && <span aria-hidden="true">↗</span>}
            </span>
          </div>
        </div>

        {/* Highlights */}
        {l.highlights && l.highlights.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {l.highlights.map((h) => (
              <span
                key={h}
                className="text-xs px-2 py-0.5 rounded bg-[#1e1e2e] text-slate-400"
              >
                {h}
              </span>
            ))}
          </div>
        )}

        {clickable && (
          <p className="text-xs text-indigo-400/80 mt-2">
            View original listing on {l.source} →
          </p>
        )}
      </div>
    </>
  );
}

export default function ListingCards({ listings }: { listings: Listing[] }) {
  if (!listings?.length) return null;

  return (
    <div className="space-y-3">
      {listings.map((l) =>
        l.url ? (
          <a
            key={l.rank}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            title={`View on ${l.source}`}
            className="flex items-start gap-4 p-4 rounded-xl bg-[#0d0d15] border border-[#1e1e2e] transition-colors duration-200 hover:border-indigo-500/50 hover:bg-[#11111c] cursor-pointer"
          >
            <ListingBody l={l} />
          </a>
        ) : (
          <div
            key={l.rank}
            className="flex items-start gap-4 p-4 rounded-xl bg-[#0d0d15] border border-[#1e1e2e] transition-colors duration-200 hover:border-indigo-500/30"
          >
            <ListingBody l={l} />
          </div>
        )
      )}
    </div>
  );
}
