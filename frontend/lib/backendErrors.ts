/**
 * Turns a backend fetch failure into something a user can actually act on.
 *
 * The backend runs on Render's free tier, which spins the instance down
 * after ~15 minutes of inactivity. The first request after that has to wait
 * for a cold start (typically 30-60s). Previously any such failure surfaced
 * as `Backend unreachable: fetch failed` or "please check the server is
 * running" — raw internals, and advice aimed at a developer rather than
 * someone trying to rent a flat. Both read as "this product is broken"
 * when the real answer is "it's waking up, try once more".
 */

export type BackendErrorCode = "timeout" | "unreachable" | "unknown";

export interface BackendError {
  code: BackendErrorCode;
  message: string;
}

const MESSAGES: Record<BackendErrorCode, string> = {
  timeout:
    "The server is taking longer than usual to respond — it goes to sleep when idle and can take up to a minute to wake up. Please try that search again.",
  unreachable:
    "Couldn't reach the server just now. It may be starting back up — please try again in a moment.",
  unknown: "Something went wrong while running that search. Please try again.",
};

/** Classify a thrown fetch error. Accepts unknown — callers catch `any`. */
export function classifyBackendError(err: unknown): BackendError {
  const name = (err as { name?: string })?.name ?? "";
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const text = raw.toLowerCase();

  // AbortSignal.timeout() throws TimeoutError; some runtimes surface an
  // AbortError with "timeout" in the message instead.
  if (name === "TimeoutError" || text.includes("timeout") || text.includes("timed out")) {
    return { code: "timeout", message: MESSAGES.timeout };
  }

  // Node/undici connection failures: "fetch failed", ECONNREFUSED, ENOTFOUND.
  if (
    text.includes("fetch failed") ||
    text.includes("econnrefused") ||
    text.includes("enotfound") ||
    text.includes("network")
  ) {
    return { code: "unreachable", message: MESSAGES.unreachable };
  }

  return { code: "unknown", message: MESSAGES.unknown };
}

export const COLD_START_HINT =
  "Still waking the server up — free hosting puts it to sleep when idle, so the first search after a quiet spell can take up to a minute.";

/**
 * Whether to show the cold-start hint. True once a search has been running
 * a while with no reply at all: the backend emits its first event almost
 * immediately when awake, so silence past this threshold means it's cold —
 * not that the search itself is slow.
 */
export function shouldShowColdStartHint(
  loading: boolean,
  sourcesReceived: number,
  elapsedMs: number,
): boolean {
  return loading && sourcesReceived === 0 && elapsedMs >= 6000;
}
