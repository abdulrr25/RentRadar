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
  safety: "Safety",
  water_supply: "Water Supply",
  traffic: "Traffic",
  food_options: "Food & Dining",
  public_transport: "Public Transport",
  overall: "Overall",
};

function scoreGradient(score: number): string {
  if (score >= 8) return "from-emerald-500 to-green-400";
  if (score >= 6) return "from-amber-500 to-yellow-400";
  return "from-red-500 to-rose-400";
}

function ScoreRow({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: number;
  emphasis?: boolean;
}) {
  const pct = Math.min((value / 10) * 100, 100);
  return (
    <div className="flex items-center gap-3">
      <span
        className={`w-32 flex-shrink-0 text-sm ${
          emphasis ? "font-semibold text-slate-200" : "text-slate-400"
        }`}
      >
        {label}
      </span>
      <div className={`flex-1 overflow-hidden rounded-full bg-white/[0.06] ${emphasis ? "h-2.5" : "h-2"}`}>
        <div
          className={`score-bar-fill h-full rounded-full bg-gradient-to-r ${scoreGradient(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`w-9 text-right tabular-nums ${
          emphasis ? "text-base font-bold text-white" : "text-sm font-semibold text-slate-300"
        }`}
      >
        {value.toFixed(1)}
      </span>
    </div>
  );
}

export default function LocalityScores({ scores }: { scores: Scores }) {
  const entries = Object.entries(scores).filter(([key]) => key !== "overall");
  const overall = scores.overall;

  return (
    <div className="space-y-3">
      {entries.map(([key, value]) =>
        value == null ? null : (
          <ScoreRow key={key} label={SCORE_LABELS[key] ?? key} value={value} />
        )
      )}

      {overall != null && (
        <div className="border-t border-white/[0.06] pt-3">
          <ScoreRow label="Overall" value={overall} emphasis />
        </div>
      )}
    </div>
  );
}
