export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <div className="badge">404</div>
      <h1 className="mt-6 font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
        This page wandered off <span className="gradient-text">the map.</span>
      </h1>
      <p className="mt-3 max-w-sm text-sm text-slate-500">
        The page you're looking for doesn't exist, or the link is out of date.
      </p>
      <a
        href="/"
        className="mt-7 inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-all active:scale-[0.97]"
        style={{ background: "linear-gradient(135deg, #4f46e5 0%, #6d28d9 100%)", boxShadow: "0 1px 3px rgba(79,70,229,0.4), 0 4px 12px -2px rgba(79,70,229,0.25)" }}
      >
        Back to search
      </a>
    </div>
  );
}
