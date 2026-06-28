"use client";

const STEPS = [
  {
    icon: "💬",
    title: "Ask in plain English",
    body: "Type what you want — “2BHK near Bellandur under ₹25,000”. No filters, no forms.",
  },
  {
    icon: "⚡",
    title: "Six sources, in parallel",
    body: "RentRadar fires NoBroker, OLX, Housing.com, Reddit, news and HN at once and reads them all.",
  },
  {
    icon: "📋",
    title: "One intelligent brief",
    body: "Ranked listings, locality scores, price trend, community pulse and scam alerts — together.",
  },
];

const SOURCES = ["NoBroker", "OLX", "Housing.com", "Reddit", "Google News", "Hacker News"];

export default function HowItWorks() {
  return (
    <section className="mx-auto max-w-5xl px-5 pb-24">
      {/* trust strip */}
      <div className="mb-16 flex flex-col items-center gap-4">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
          Aggregating real-time data from
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2.5">
          {SOURCES.map((s) => (
            <span
              key={s}
              className="glass rounded-full px-4 py-1.5 text-sm font-medium text-slate-300"
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* how it works */}
      <div className="text-center mb-10">
        <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-white">
          How it works
        </h2>
        <p className="mt-2 text-sm text-slate-400">From question to decision in three steps.</p>
      </div>

      <div className="grid gap-5 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <div
            key={step.title}
            className="glass gradient-border group relative overflow-hidden rounded-2xl p-6 transition duration-300 hover:bg-white/[0.05]"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/10 text-xl ring-1 ring-white/10">
                {step.icon}
              </span>
              <span className="font-display text-sm font-semibold text-indigo-300/80">
                Step {i + 1}
              </span>
            </div>
            <h3 className="mt-4 font-display text-lg font-semibold text-white">
              {step.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{step.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
