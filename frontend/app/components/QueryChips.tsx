"use client";

/**
 * What RentRadar actually understood from the query, stated plainly.
 *
 * The backend only ever filters on locality / BHK / budget; everything else
 * a user types ("furnished", "near metro", "ground floor") either ranks
 * results or isn't understood at all. Showing only the three filters — as
 * this did before — reads as "we understood your whole query", so a search
 * for "pet friendly 1BHK under 25k ground floor" looked fully honoured when
 * two thirds of it had been dropped. Listing the preferences we did pick up,
 * and saying out loud that they rank rather than exclude, makes the gap
 * visible instead of silent.
 */

interface Props {
  parsedQuery: {
    locality?: string;
    bhk?: string;
    max_rent?: number;
    min_rent?: number | null;
    preferences?: string[];
  };
}

const PREFERENCE_LABELS: Record<string, string> = {
  furnished: "Furnished",
  semi_furnished: "Semi-furnished",
  unfurnished: "Unfurnished",
  parking: "Parking",
  metro: "Near metro",
  pet_friendly: "Pet friendly",
  no_broker: "Owner direct",
  gated: "Gated community",
  family: "Family",
  bachelors: "Bachelors",
};

const PIN = (
  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" /><circle cx="12" cy="10" r="3" />
  </svg>
);

const BED = (
  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 4v16" /><path d="M2 8h18a2 2 0 0 1 2 2v10" /><path d="M2 17h20" /><path d="M6 8v9" />
  </svg>
);

const RUPEE = (
  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 3h12" /><path d="M6 8h12" /><path d="M6 13 15 21" /><path d="M6 13h3c3 0 5-1.5 5-5" />
  </svg>
);

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN")}`;
}

export default function QueryChips({ parsedQuery }: Props) {
  const { locality, bhk, max_rent, min_rent } = parsedQuery;
  const preferences = parsedQuery.preferences ?? [];

  const budget =
    max_rent == null
      ? null
      : min_rent != null
        ? `${inr(min_rent)} – ${inr(max_rent)}`
        : `max ${inr(max_rent)}`;

  const filters = [
    { key: "locality", icon: PIN, val: locality },
    { key: "bhk", icon: BED, val: bhk },
    { key: "budget", icon: RUPEE, val: budget },
  ].filter((f) => f.val);

  return (
    <div className="mt-4">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        Searching for
      </p>

      <div className="flex flex-wrap gap-2">
        {filters.map(({ key, icon, val }) => (
          <span
            key={key}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-1 text-xs font-medium text-slate-600"
            style={{ boxShadow: "0 1px 2px rgba(15,23,42,0.05)" }}
          >
            {icon} {val}
          </span>
        ))}

        {/* Visually lighter than the filter chips above — these change the
            order of results, they don't narrow them. */}
        {preferences.map((p) => (
          <span
            key={p}
            className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-brand-200 bg-brand-50 px-3.5 py-1 text-xs font-medium text-brand-700"
          >
            {PREFERENCE_LABELS[p] ?? p}
          </span>
        ))}
      </div>

      {preferences.length > 0 && (
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
          Locality, home type and budget are applied as filters. The dashed items are used
          to rank results — listings that don&apos;t mention them are still shown.
        </p>
      )}
    </div>
  );
}
