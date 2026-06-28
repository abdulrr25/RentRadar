"use client";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

interface Props {
  sources: string[];
  statuses: Record<string, SourceStatus>;
}

const STATUS_STYLES: Record<SourceStatus, string> = {
  idle:     "border-white/[0.07] bg-white/[0.03] text-slate-500",
  fetching: "border-indigo-600/50 bg-indigo-500/10 text-indigo-200 pill-fetching",
  ok:       "border-emerald-600/40 bg-emerald-500/10 text-emerald-300",
  error:    "border-red-700/40 bg-red-500/10 text-red-300",
};

const STATUS_DOT: Record<SourceStatus, string> = {
  idle:     "bg-slate-600",
  fetching: "bg-indigo-400 animate-pulse",
  ok:       "bg-emerald-400",
  error:    "bg-red-400",
};

function StatusGlyph({ status }: { status: SourceStatus }) {
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
  return <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />;
}

export default function SourceIndicators({ sources, statuses }: Props) {
  if (!sources.length) return null;

  const done = sources.filter((s) => statuses[s] === "ok" || statuses[s] === "error").length;

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center justify-center gap-2">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
          Live data sources
        </p>
        <span className="rounded-full bg-white/[0.05] px-2 py-0.5 text-[10px] font-semibold text-slate-400">
          {done}/{sources.length}
        </span>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {sources.map((src) => {
          const status = statuses[src] ?? "idle";
          return (
            <span
              key={src}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 ${STATUS_STYLES[status]}`}
            >
              <StatusGlyph status={status} />
              {src}
            </span>
          );
        })}
      </div>
    </div>
  );
}
