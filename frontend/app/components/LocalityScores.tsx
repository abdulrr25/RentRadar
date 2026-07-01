"use client";

interface Scores {
  safety?: number;
  water_supply?: number;
  traffic?: number;
  food_options?: number;
  public_transport?: number;
  overall?: number;
}

const SCORE_LABELS: Record<string, string> = {
  safety:           "Safety",
  water_supply:     "Water Supply",
  traffic:          "Traffic",
  food_options:     "Food & Dining",
  public_transport: "Transport",
  overall:          "Overall",
};

function scoreColor(score: number) {
  if (score >= 8) return { bar: "from-emerald-500 to-green-400", text: "text-emerald-400" };
  if (score >= 6) return { bar: "from-amber-500 to-yellow-400", text: "text-amber-400" };
  return { bar: "from-red-500 to-rose-400", text: "text-red-400" };
}

/* Circular SVG indicator for the Overall score */
function OverallRing({ value }: { value: number }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const fill = Math.min(value / 10, 1) * circ;
  const { text } = scoreColor(value);

  return (
    <div className="flex flex-col items-center gap-2 py-4">
      <div className="relative">
        <svg width="80" height="80" viewBox="0 0 80 80">
          {/* Track */}
          <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="5" />
          {/* Fill */}
          <circle
            cx="40" cy="40" r={r}
            fill="none"
            stroke="url(#scoreGrad)"
            strokeWidth="5"
            strokeDasharray={`${fill} ${circ}`}
            strokeDashoffset={circ / 4}
            strokeLinecap="round"
            className="score-bar-fill"
            style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.16,1,0.3,1)" }}
          />
          <defs>
            <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
          {/* Value text */}
          <text x="40" y="44" textAnchor="middle" className="fill-white" style={{ fontSize: 20, fontWeight: 700, fontFamily: "inherit" }}>
            {value.toFixed(1)}
          </text>
        </svg>
      </div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Overall Score</p>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  const { bar, text } = scoreColor(value);
  const pct = Math.min((value / 10) * 100, 100);

  return (
    <div className="flex items-center gap-3">
      <span className="w-24 sm:w-28 flex-shrink-0 text-xs text-slate-400">{label}</span>
      <div className="flex-1 overflow-hidden rounded-full bg-white/[0.06] h-1.5">
        <div
          className={`score-bar-fill h-full rounded-full bg-gradient-to-r ${bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`w-8 text-right text-xs font-semibold tabular-nums ${text}`}>
        {value.toFixed(1)}
      </span>
    </div>
  );
}

export default function LocalityScores({ scores }: { scores: Scores }) {
  const entries = Object.entries(scores).filter(([key]) => key !== "overall");
  const overall = scores.overall;

  return (
    <div className="space-y-2.5">
      {entries.map(([key, value]) =>
        value == null ? null : (
          <ScoreRow key={key} label={SCORE_LABELS[key] ?? key} value={value} />
        )
      )}
      {overall != null && (
        <div className="border-t border-white/[0.055] pt-4 mt-4">
          <OverallRing value={overall} />
        </div>
      )}
    </div>
  );
}
