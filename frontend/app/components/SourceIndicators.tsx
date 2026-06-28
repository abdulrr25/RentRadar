"use client";

type SourceStatus = "idle" | "fetching" | "ok" | "error";

interface Props {
  sources: string[];
  statuses: Record<string, SourceStatus>;
}

const STATUS_STYLES: Record<SourceStatus, string> = {
  idle:     "bg-[#1e1e2e] text-slate-500 border border-[#2a2a3e]",
  fetching: "bg-indigo-950 text-indigo-300 border border-indigo-700/60 pill-fetching",
  ok:       "bg-emerald-950 text-emerald-400 border border-emerald-700/60",
  error:    "bg-red-950 text-red-400 border border-red-700/60",
};

const STATUS_DOT: Record<SourceStatus, string> = {
  idle:     "bg-slate-600",
  fetching: "bg-indigo-400 animate-pulse",
  ok:       "bg-emerald-400",
  error:    "bg-red-400",
};

export default function SourceIndicators({ sources, statuses }: Props) {
  if (!sources.length) return null;

  return (
    <div className="w-full max-w-2xl mx-auto">
      <p className="text-xs text-slate-500 mb-3 uppercase tracking-wider font-medium">
        Live data sources
      </p>
      <div className="flex flex-wrap gap-2">
        {sources.map((src) => {
          const status = statuses[src] ?? "idle";
          return (
            <span
              key={src}
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                transition-all duration-300 ${STATUS_STYLES[status]}
              `}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status]}`} />
              {src}
            </span>
          );
        })}
      </div>
    </div>
  );
}
