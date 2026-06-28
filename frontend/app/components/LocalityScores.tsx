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
  public_transport: "Public Transport",
  overall:          "Overall",
};

function scoreColor(score: number): string {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 6) return "bg-yellow-500";
  return "bg-red-500";
}

function scoreWarning(score: number): string {
  if (score < 5) return " ⚠️";
  if (score < 7) return " ·";
  return "";
}

export default function LocalityScores({ scores }: { scores: Scores }) {
  const entries = Object.entries(scores).filter(
    ([key]) => key !== "overall"
  );
  const overall = scores.overall;

  return (
    <div className="space-y-2.5">
      {entries.map(([key, value]) => {
        if (value == null) return null;
        const pct = Math.min((value / 10) * 100, 100);
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="w-36 text-sm text-slate-400 shrink-0">
              {SCORE_LABELS[key] ?? key}
              <span className="text-amber-400">{scoreWarning(value)}</span>
            </span>
            <div className="flex-1 bg-[#1e1e2e] rounded-full h-2">
              <div
                className={`h-2 rounded-full score-bar-fill ${scoreColor(value)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-8 text-right text-sm font-semibold text-slate-300">
              {value.toFixed(1)}
            </span>
          </div>
        );
      })}

      {overall != null && (
        <div className="flex items-center gap-3 pt-2 border-t border-[#1e1e2e]">
          <span className="w-36 text-sm font-semibold text-slate-200 shrink-0">Overall</span>
          <div className="flex-1 bg-[#1e1e2e] rounded-full h-3">
            <div
              className={`h-3 rounded-full score-bar-fill ${scoreColor(overall)}`}
              style={{ width: `${Math.min((overall / 10) * 100, 100)}%` }}
            />
          </div>
          <span className="w-8 text-right text-base font-bold text-slate-100">
            {overall.toFixed(1)}
          </span>
        </div>
      )}
    </div>
  );
}
