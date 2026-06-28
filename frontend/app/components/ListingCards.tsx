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
  NoBroker: "bg-green-500/15 text-green-300 border-green-600/30",
  OLX: "bg-purple-500/15 text-purple-300 border-purple-600/30",
  "Housing.com": "bg-blue-500/15 text-blue-300 border-blue-600/30",
};

function ListingBody({ l }: { l: Listing }) {
  const clickable = Boolean(l.url);
  return (
    <>
      {/* Rank badge */}
      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/10 text-sm font-bold text-indigo-300 ring-1 ring-white/10">
        {l.rank}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-100">{l.locality_detail}</p>
            {l.commute_note && (
              <p className="mt-0.5 text-xs text-slate-500">{l.commute_note}</p>
            )}
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            <span className="font-display text-lg font-bold text-emerald-400">
              ₹{l.rent.toLocaleString("en-IN")}
              <span className="text-sm font-normal text-slate-500">/mo</span>
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${
                SOURCE_BADGE[l.source] ?? "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              {l.source}
              {clickable && <span aria-hidden="true">↗</span>}
            </span>
          </div>
        </div>

        {l.highlights && l.highlights.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {l.highlights.map((h) => (
              <span
                key={h}
                className="rounded-md bg-white/[0.04] px-2 py-0.5 text-xs text-slate-400"
              >
                {h}
              </span>
            ))}
          </div>
        )}

        {clickable && (
          <p className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-indigo-400 transition group-hover:gap-1.5 group-hover:text-indigo-300">
            View original listing on {l.source}
            <span aria-hidden="true">→</span>
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
            className="group flex items-start gap-4 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4 transition duration-200 hover:-translate-y-0.5 hover:border-indigo-500/40 hover:bg-white/[0.045] hover:shadow-glow-sm"
          >
            <ListingBody l={l} />
          </a>
        ) : (
          <div
            key={l.rank}
            className="group flex items-start gap-4 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4 transition duration-200 hover:border-white/15"
          >
            <ListingBody l={l} />
          </div>
        )
      )}
    </div>
  );
}
