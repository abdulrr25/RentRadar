"use client";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

interface Props {
  sources: string[];
  statuses: Record<string, SourceStatus>;
}

const PILL: Record<SourceStatus, string> = {
  idle:     "border-white/[0.07] text-slate-600",
  fetching: "border-indigo-500/40 text-indigo-300 pill-fetching",
  ok:       "border-emerald-600/30 text-emerald-300",
  error:    "border-red-700/35 text-red-400",
};

const PILL_BG: Record<SourceStatus, string> = {
  idle:     "rgba(255,255,255,0.02)",
  fetching: "rgba(99,102,241,0.07)",
  ok:       "rgba(16,185,129,0.06)",
  error:    "rgba(239,68,68,0.06)",
};

function StatusIcon({ status }: { status: SourceStatus }) {
  if (status === "ok")
    return (
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    );
  if (status === "error")
    return (
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 6 6 18M6 6l12 12" />
      </svg>
    );
  if (status === "fetching")
    return <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />;
  return <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />;
}

export default function SourceIndicators({ sources, statuses }: Props) {
  if (!sources.length) return null;

  const done  = sources.filter((s) => statuses[s] === "ok" || statuses[s] === "error").length;
  const total = sources.length;
  const pct   = total > 0 ? (done / total) * 100 : 0;

  return (
    <div className="w-full space-y-4">
      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10.5px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Scanning sources
          </p>
          <span className="text-[10.5px] font-semibold tabular-nums text-slate-400">
            {done}/{total}
          </span>
        </div>
        <div className="h-[3px] w-full overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: done === total
                ? "linear-gradient(90deg, #10b981, #34d399)"
                : "linear-gradient(90deg, #6366f1, #a78bfa)",
            }}
          />
        </div>
      </div>

      {/* Source pills */}
      <div className="flex flex-wrap gap-2">
        {sources.map((src) => {
          const status = statuses[src] ?? "idle";
          return (
            <span
              key={src}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all duration-300 ${PILL[status]}`}
              style={{ background: PILL_BG[status] }}
            >
              <StatusIcon status={status} />
              {src}
            </span>
          );
        })}
      </div>
    </div>
  );
}
