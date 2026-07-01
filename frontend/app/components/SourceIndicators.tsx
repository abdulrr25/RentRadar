"use client";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

interface Props {
  sources: string[];
  statuses: Record<string, SourceStatus>;
}

/* Listing portals = critical. Sentiment sources = optional context. */
const LISTING_SOURCES = new Set(["NoBroker", "OLX", "Housing.com"]);

function pill(status: SourceStatus, isSentiment: boolean) {
  if (status === "ok")       return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "fetching") return "border-brand-200 bg-brand-50 text-brand-700 pill-fetching";
  if (status === "error")    return isSentiment
    ? "border-amber-200 bg-amber-50 text-amber-700"   // sentiment fail = amber (optional)
    : "border-red-200 bg-red-50 text-red-600";         // listing fail  = red (critical)
  return "border-slate-200 bg-white text-slate-400";
}

function StatusIcon({ status, isSentiment }: { status: SourceStatus; isSentiment: boolean }) {
  if (status === "ok")
    return (
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    );
  if (status === "error")
    return isSentiment ? (
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    ) : (
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 6 6 18M6 6l12 12" />
      </svg>
    );
  if (status === "fetching")
    return <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse" />;
  return <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />;
}

export default function SourceIndicators({ sources, statuses }: Props) {
  if (!sources.length) return null;

  const done  = sources.filter((s) => statuses[s] === "ok" || statuses[s] === "error").length;
  const total = sources.length;
  const pct   = total > 0 ? (done / total) * 100 : 0;
  const allDone = done === total;

  return (
    <div className="w-full space-y-4">
      {/* Progress */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-[0.14em]">
            {allDone ? "Scan complete" : "Scanning sources"}
          </p>
          <span className="text-xs font-semibold text-slate-600 tabular-nums">{done}/{total}</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: allDone
                ? "linear-gradient(90deg, #10b981, #34d399)"
                : "linear-gradient(90deg, #4f46e5, #7c3aed)",
            }}
          />
        </div>
        {/* Note about sentiment failures */}
        {allDone && sources.some((s) => !LISTING_SOURCES.has(s) && statuses[s] === "error") &&
          sources.some((s) => LISTING_SOURCES.has(s) && statuses[s] === "ok") && (
          <p className="mt-2 text-[11px] text-amber-600">
            Some sentiment sources (Google News / HN) were unavailable — listings are unaffected.
          </p>
        )}
      </div>

      {/* Pills */}
      <div className="flex flex-wrap gap-2">
        {sources.map((src) => {
          const status = statuses[src] ?? "idle";
          const isSentiment = !LISTING_SOURCES.has(src);
          return (
            <span
              key={src}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all duration-300 ${pill(status, isSentiment)}`}
            >
              <StatusIcon status={status} isSentiment={isSentiment} />
              {src}
              {status === "error" && isSentiment && (
                <span className="text-[10px] opacity-70">limited</span>
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
}
