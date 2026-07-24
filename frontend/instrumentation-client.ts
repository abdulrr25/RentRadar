import * as Sentry from "@sentry/nextjs";

// No-op until NEXT_PUBLIC_SENTRY_DSN is set — Sentry.init() with an empty
// dsn just doesn't send anything, same stubbed-until-configured pattern as
// every backend integration in this project.
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "production",
  tracesSampleRate: 0.1,
  // No session replay — this app has no auth and every screen already
  // shows only public rental-search data, but replay defaults to masking
  // aggressively anyway; skipping it entirely keeps the bundle smaller.
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
