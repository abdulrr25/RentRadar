import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";
import RentRadarCard from "../../components/RentRadarCard";

// The brief is fetched at request time from the backend; content for a given
// id never changes, but we keep rendering dynamic so expired briefs 404
// promptly instead of being served from a stale static cache.
export const dynamic = "force-dynamic";

interface BriefRecord {
  locality: string;
  bhk: string;
  max_rent: number;
  brief: string;
  created_at: number;
}

// cache() dedupes the fetch between generateMetadata and the page render —
// one backend call per request, not two.
const getBrief = cache(async (id: string): Promise<BriefRecord | null> => {
  const apiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/brief/${encodeURIComponent(id)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as BriefRecord;
  } catch {
    return null;
  }
});

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const record = await getBrief(params.id);
  if (!record) return { title: "Brief not found — RentRadar" };

  const title = `${record.bhk} in ${record.locality} under ₹${record.max_rent.toLocaleString("en-IN")} — RentRadar`;
  let description = "Live rental brief: ranked listings, locality scores, price trend and scam alerts.";
  try {
    const summary = JSON.parse(record.brief)?.search_summary;
    if (typeof summary === "string" && summary.trim()) description = summary.trim();
  } catch { /* keep default */ }

  // WhatsApp/Telegram build their link-preview card from these tags at
  // scrape time (before any JS runs) — this is what makes a forwarded link
  // look like a real result card in a group chat.
  return {
    title,
    description,
    openGraph: { title, description, type: "article" },
  };
}

export default async function SharedBriefPage({ params }: { params: { id: string } }) {
  const record = await getBrief(params.id);
  if (!record) notFound();

  const snapshotDate = new Date(record.created_at * 1000).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
  const parsedQuery = { locality: record.locality, bhk: record.bhk, max_rent: record.max_rent };

  return (
    <div className="relative min-h-screen flex flex-col">
      <div className="aurora"><span className="blob-3" /></div>

      <header className="glass sticky top-0 z-30 border-b border-white/40" style={{ boxShadow: "0 1px 4px rgba(15,23,42,0.06)" }}>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600" style={{ boxShadow: "0 2px 8px rgba(79,70,229,0.35)" }}>
              <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
              </svg>
            </span>
            <span className="font-display text-[17px] font-bold tracking-tight text-slate-900">
              Rent<span className="gradient-text">Radar</span>
            </span>
          </a>
          <a
            href="/"
            className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold text-white transition-all active:scale-[0.97]"
            style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)", boxShadow: "0 1px 3px rgba(79,70,229,0.4)" }}
          >
            Run your own search
          </a>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-2xl px-4 sm:px-6 pt-8 pb-24">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-slate-500">
              Shared rental brief · snapshot from {snapshotDate} — listings and prices may have changed since.
            </p>
          </div>
          <RentRadarCard rawBrief={record.brief} parsedQuery={parsedQuery} shareId={params.id} />
        </section>
      </main>

      <footer className="glass border-t border-white/40">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <span className="font-display text-sm font-bold text-slate-700">
            Rent<span className="gradient-text">Radar</span>
          </span>
          <p>AI rental intelligence for Bangalore · Free, no sign-up · <a href="/terms" className="underline-offset-2 hover:underline">Terms</a></p>
        </div>
      </footer>
    </div>
  );
}
