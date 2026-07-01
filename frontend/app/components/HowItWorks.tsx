"use client";

const STEPS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    title: "Ask in plain English",
    body: 'Type what you need — "2BHK near Bellandur under ₹25,000". No forms, no filters, no friction.',
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
    body: "Ranked listings with real prices, locality scores, community pulse, price trend and scam alerts — all in one place.",
  },
];

const SOURCES = [
  { name: "NoBroker",    dot: "#16a34a" },
  { name: "OLX",         dot: "#9333ea" },
  { name: "Housing.com", dot: "#2563eb" },
  { name: "Reddit",      dot: "#ea580c" },
  { name: "Google News", dot: "#4f46e5" },
  { name: "Hacker News", dot: "#d97706" },
];

export default function HowItWorks() {
  return (
    <section className="border-t border-slate-300 bg-white">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 py-20">

        {/* Source trust strip */}
        <div className="mb-16 flex flex-col items-center gap-5">
          <p className="text-[10.5px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Aggregating real-time data from
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {SOURCES.map((s) => (
              <span key={s.name} className="flex items-center gap-2 rounded-full border border-slate-300 bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-700">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.dot }} />
                {s.name}
              </span>
            ))}
          </div>
        </div>

        {/* Heading */}
        <div className="text-center mb-10">
          <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">How RentRadar works</h2>
          <p className="mt-2 text-sm text-slate-500">From question to decision in three steps.</p>
        </div>

        {/* Steps */}
        <div className="grid gap-4 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:border-brand-200 hover:shadow-lift"
              style={{ boxShadow: "0 1px 3px rgba(15,23,42,0.06)" }}
            >
              {/* Watermark step number */}
              <span className="absolute top-3 right-4 font-display text-7xl font-black text-slate-50 select-none pointer-events-none leading-none">
                {i + 1}
              </span>

              <div className="relative mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 border border-brand-100 text-brand-600">
                {step.icon}
              </div>

              <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-brand-500">Step {i + 1}</p>
              <h3 className="font-display text-base font-semibold text-slate-900">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{step.body}</p>
            </div>
          ))}
        </div>

        <p className="mt-10 text-center text-xs text-slate-500">
          Powered by <span className="font-medium text-slate-700">Llama 3.3 70B</span> via Groq ·{" "}
          <span className="font-medium text-slate-700">Anakin Wire API</span> · Free, no account required
        </p>
      </div>
    </section>
  );
}
