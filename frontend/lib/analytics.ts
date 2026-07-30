/**
 * Minimal privacy-respecting product analytics — no-op until
 * NEXT_PUBLIC_UMAMI_WEBSITE_ID is set, same stubbed-until-configured pattern
 * as every other integration in this project (Telegram, Web Push, Sentry, ...).
 *
 * Right now there's zero visibility into search volume, which alert channel
 * gets used, or where people drop off — every product decision from here is
 * a guess. Wired to Umami specifically: genuinely open-source (MIT,
 * self-hostable for zero cost on a cheap VPS), and its hosted Cloud tier is
 * a real permanent free plan — not a 14-day trial like Sentry's.
 *
 * No client SDK needed — Umami's /api/send endpoint takes a plain JSON POST
 * and needs no API key (identified by the public website ID only, same
 * "safe to expose" pattern as a VAPID public key). That also means zero
 * bundle weight even when configured, unlike a full analytics SDK.
 */

const UMAMI_HOST = process.env.NEXT_PUBLIC_UMAMI_HOST ?? "https://cloud.umami.is";
const UMAMI_WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID;

/** Shared payload — Umami identifies the visitor from these + the request IP. */
function basePayload() {
  return {
    website: UMAMI_WEBSITE_ID,
    // pathname + search, not pathname alone: campaign tags (?utm_source=...)
    // live in the query string, and dropping it makes it impossible to tell
    // which channel a visitor came from. Nothing sensitive is ever put in a
    // URL here — searches are POSTed, not query-encoded.
    url: window.location.pathname + window.location.search,
    hostname: window.location.hostname,
    language: navigator.language,
    screen: `${window.screen.width}x${window.screen.height}`,
    title: document.title,
    referrer: document.referrer,
  };
}

function send(payload: Record<string, unknown>): void {
  fetch(`${UMAMI_HOST}/api/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "event", payload }),
  }).catch(() => {
    /* analytics must never break the app */
  });
}

/**
 * Record a page view.
 *
 * This is what actually produces visitor / session counts. Umami treats a
 * payload WITHOUT a `name` as a pageview and one WITH a `name` as a custom
 * event — so the custom events below can never answer "how many people
 * reached the site", because every one of them requires the visitor to
 * click something first. Anyone who lands and bounces would otherwise be
 * counted as nobody at all.
 */
export function trackPageview(): void {
  if (!UMAMI_WEBSITE_ID || typeof window === "undefined") return;
  send(basePayload());
}

/**
 * Fire-and-forget event tracking. Safe to call unconditionally from any
 * component — it's a true no-op (not even a network request) when
 * NEXT_PUBLIC_UMAMI_WEBSITE_ID isn't set.
 */
export function track(event: string, properties?: Record<string, unknown>): void {
  if (!UMAMI_WEBSITE_ID || typeof window === "undefined") return;
  send({ ...basePayload(), name: event, data: properties });
}
