"use client";

const STEPS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    title: "Ask in plain English",
    body: "Type what you need — "2BHK near Bellandur under ₹25,000". No forms, no filters, no friction.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
      </svg>
    ),
    title: "Six sources, in parallel",
    body: "NoBroker, OLX, Housing.com, Reddit, Google News and Hacker News — all scanned simultaneously in under 15 seconds.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
      </svg>
    ),
    title: "One intelligent brief",
    body: "Ranked listings with real prices, locality scores, community pulse, price trend and scam alerts — one place.",
  },
];

const SOURCES = [
  { name: "NoBroker",    color: "#22c55e" },
  { name: "OLX",         color: "#a855f7" },
  { name: "Housing.com", color: "#3b82f6" },
  { name: "Reddit",      color: "#f97316" },
  { name: "Google News", color: "#6366f1" },
  { name: "Hacker News", color: "#f59e0b" },
];

export default function HowItWorks() {
  return (
    <section className="mx-auto max-w-5xl px-4 sm:px-6 pb-24">

      {/* Source trust strip */}
      <div className="mb-16 flex flex-col items-center gap-5">
        <p className="text-[10.5px] uppercase tracking-[0.22em] text-slate-600">
          Aggregating real-time data from
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {SOURCES.map((s) => (
            <span
              key={s.name}
              className="flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium text-slate-400 border border-white/[0.07]"
              style={{ background: "rgba(255,255,255,0.025)" }}
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="text-center mb-10">
        <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-white">
          How RentRadar works
        </h2>
        <p className="mt-2 text-sm text-slate-500">From question to decision in three steps.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <div
            key={step.title}
            className="group relative overflow-hidden rounded-2xl border border-white/[0.075] p-6 transition-all duration-300 hover:border-indigo-500/30 hover:-translate-y-0.5"
            style={{ background: "linear-gradient(160deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.012) 100%)" }}
          >
            {/* Step number watermark */}
            <span
              className="absolute top-4 right-5 font-display text-6xl font-black leading-none select-none pointer-events-none transition-opacity duration-300 group-hover:opacity-[0.04]"
              style={{ color: "rgba(255,255,255,0.03)" }}
            >
              {i + 1}
            </span>

            <div
              className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl text-indigo-300"
              style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.18)" }}
            >
              {step.icon}
            </div>

            <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-400/70">
              Step {i + 1}
            </p>
            <h3 className="font-display text-base font-semibold text-white">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">{step.body}</p>
          </div>
        ))}
      </div>

      {/* Bottom CTA hint */}
      <p className="mt-10 text-center text-xs text-slate-600">
        Powered by <span className="text-slate-500">Llama 3.3 70B</span> via Groq ·{" "}
        <span className="text-slate-500">Anakin Wire API</span> · Free, no account needed
      </p>
    </section>
  );
}
