/**
 * The SSE event-parsing state machine, extracted into pure functions.
 *
 * This used to live entirely inline inside page.tsx's fetch loop — the most
 * fragile logic in the app (malformed JSON, split network chunks, an abort
 * mid-stream) with zero test coverage. Nothing here does I/O, so all of it
 * is directly unit-testable without a browser or a real network stream.
 */

export type SourceStatus = "idle" | "fetching" | "ok" | "error";

export const ALL_SOURCES = ["Reddit", "Google News", "Hacker News", "NoBroker", "OLX", "Housing.com"];

export interface SearchState {
  loading: boolean;
  sources: string[];
  statuses: Record<string, SourceStatus>;
  brief: string | null;
  error: string | null;
  parsedQuery: Record<string, any> | null;
  shareId: string | null;
}

export const initialSearchState: SearchState = {
  loading: false,
  sources: [],
  statuses: {},
  brief: null,
  error: null,
  parsedQuery: null,
  shareId: null,
};

export type SSEEvent =
  | { type: "parsed"; data: Record<string, any> }
  | { type: "fetching"; sources?: string[] }
  | { type: "source_complete"; source: string; status: string }
  | { type: "brief"; data: string }
  | { type: "share"; id?: string | null }
  | { type: "done" }
  | { type: "error"; message?: string };

export type SearchAction =
  | SSEEvent
  | { type: "reset" }
  | { type: "aborted" };

export function searchReducer(state: SearchState, action: SearchAction): SearchState {
  switch (action.type) {
    case "reset":
      return { ...initialSearchState, loading: true };

    case "aborted":
      // A self-inflicted abort (user fired a new search before the previous
      // one finished) — silently clear any stale error, never show a
      // "backend unreachable" message for it.
      return { ...state, error: null, loading: false };

    case "parsed":
      return { ...state, parsedQuery: action.data };

    case "fetching": {
      const sources = action.sources ?? ALL_SOURCES;
      return {
        ...state,
        sources,
        statuses: Object.fromEntries(sources.map((s) => [s, "fetching" as const])),
      };
    }

    case "source_complete":
      return {
        ...state,
        statuses: { ...state.statuses, [action.source]: action.status === "ok" ? "ok" : "error" },
      };

    case "brief":
      return { ...state, brief: action.data };

    case "share":
      return { ...state, shareId: action.id ?? null };

    case "done":
      return { ...state, loading: false };

    case "error":
      return { ...state, error: action.message ?? "Something went wrong.", loading: false };

    default:
      return state;
  }
}

/**
 * Splits an accumulated SSE byte-stream buffer into complete "data: ..."
 * lines, plus the trailing partial line to prepend to the next chunk (a
 * chunk boundary can land mid-line at any point in a real network stream).
 */
export function splitSSEBuffer(buffer: string): { lines: string[]; remainder: string } {
  const parts = buffer.split("\n");
  const remainder = parts.pop() ?? "";
  const lines = parts.filter((line) => line.startsWith("data: "));
  return { lines, remainder };
}

/** Parses one "data: {...}" line into an event, or null if malformed. */
export function parseSSELine(line: string): SSEEvent | null {
  try {
    return JSON.parse(line.slice(6));
  } catch {
    return null;
  }
}
