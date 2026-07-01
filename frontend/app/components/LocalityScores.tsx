"use client";

interface Scores {
  safety?: number;
  water_supply?: number;
  traffic?: number;
  food_options?: number;
  public_transport?: number;
  overall?: number;
}

const LABELS: Record<string, string> = {
  safety: "Safety", water_supply: "Water Supply", traffic: "Traffic",
  food_options: "Food & Dining", public_transport: "Transport", overall: "Overall",
};

function scoreStyle(v: number) {
  if (v >= 8) return { bar: "from-emerald-500 to-green-400", text: "text-emerald-600", track: "bg-emerald-100" };
  if (v >= 6) return { bar: "from-amber-500 to-yellow-400", text: "text-amber-600",   track: "bg-amber-100"  };
  return              { bar: "from-red-500 to-rose-400",     text: "text-red-600",     track: "bg-red-100"    };
}

function OverallRing({ value }: { value: number }) {
  const r = 30, circ = 2 * Math.PI * r;
  const fill = Math.min(value / 10, 1) * circ;
  const s = scoreStyle(value);

  return (
    <div className="flex flex-col items-center gap-3 py-4">
      <div className="relative">
        <svg width="88" height="88" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r={r} fill="none" stroke="#f1f5f9" strokeWidth="6" />
          <circle
            cx="44" cy="44" r={r}
            fill="none"
            stroke="url(#ringGrad)"
            strokeWidth="6"
            strokeDasharray={`${fill} ${circ}`}
            strokeDashoffset={circ / 4}
            strokeLinecap="round"
            className="score-bar-fill"
          />
          <defs>
            <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#4f46e5" /><stop offset="100%" stopColor="#7c3aed" />
            </linearGradient>
          </defs>
          <text x="44" y="49" textAnchor="middle" className="fill-slate-900" style={{ fontSize: 21, fontWeight: 700, fontFamily: "inherit" }}>
            {value.toFixed(1)}
          </text>
        </svg>
      </div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Overall Score</p>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  const { bar, text, track } = scoreStyle(value);
  const pct = Math.min((value / 10) * 100, 100);
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 sm:w-28 flex-shrink-0 text-xs text-slate-500">{label}</span>
      <div className={`flex-1 overflow-hidden rounded-full h-1.5 ${track}`}>
        <div className={`score-bar-fill h-full rounded-full bg-gradient-to-r ${bar}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`w-8 text-right text-xs font-semibold tabular-nums ${text}`}>{value.toFixed(1)}</span>
    </div>
  );
}

export default function LocalityScores({ scores }: { scores: Scores }) {
  const entries = Object.entries(scores).filter(([k]) => k !== "overall");
  return (
    <div className="space-y-2.5">
      {entries.map(([k, v]) => v == null ? null : <ScoreRow key={k} label={LABELS[k] ?? k} value={v} />)}
      {scores.overall != null && (
        <div className="border-t border-slate-100 pt-4 mt-4">
          <OverallRing value={scores.overall} />
        </div>
      )}
    </div>
  );
}
