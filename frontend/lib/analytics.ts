/**
 * Minimal privacy-respecting product analytics — no-op until
 * NEXT_PUBLIC_POSTHOG_KEY is set, same stubbed-until-configured pattern as
 * every other integration in this project (Telegram, Web Push, Sentry, ...).
 *
 * Right now there's zero visibility into search volume, which alert channel
 * gets used, or where people drop off — every product decision from here is
 * a guess. Wired to PostHog specifically because it has a genuine permanent
 * free tier (1M events/month, no card) — not a 14-day trial like Sentry's.
 *
 * The posthog-js import is dynamic and only reached if a key is configured,
 * so an unconfigured deployment never fetches the analytics chunk at all —
 * zero runtime cost, not just zero events sent.
 */

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";

let initPromise: Promise<typeof import("posthog-js").default> | null = null;

async function getClient() {
  if (!POSTHOG_KEY || typeof window === "undefined") return null;
  if (!initPromise) {
    initPromise = import("posthog-js").then(({ default: posthog }) => {
      posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        capture_pageview: true,
        autocapture: false, // explicit track() calls only — no click-guessing
      });
      return posthog;
    });
  }
  return initPromise;
}

/**
 * Fire-and-forget event tracking. Safe to call unconditionally from any
 * component — it's a true no-op (not even a network request) when
 * NEXT_PUBLIC_POSTHOG_KEY isn't set.
 */
export function track(event: string, properties?: Record<string, unknown>): void {
  if (!POSTHOG_KEY || typeof window === "undefined") return;
  getClient()
    .then((client) => client?.capture(event, properties))
    .catch(() => {
      /* analytics must never break the app */
    });
}
