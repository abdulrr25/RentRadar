import { describe, it, expect } from "vitest";
import {
  searchReducer,
  initialSearchState,
  splitSSEBuffer,
  parseSSELine,
  ALL_SOURCES,
} from "../searchReducer";

describe("searchReducer", () => {
  it("reset clears prior state and sets loading", () => {
    const dirty = { ...initialSearchState, brief: "stale", error: "stale error", loading: false };
    const next = searchReducer(dirty, { type: "reset" });
    expect(next).toEqual({ ...initialSearchState, loading: true });
  });

  it("aborted clears error without setting a message", () => {
    const withError = { ...initialSearchState, error: "some earlier error", loading: true };
    const next = searchReducer(withError, { type: "aborted" });
    expect(next.error).toBeNull();
    expect(next.loading).toBe(false);
  });

  it("parsed sets parsedQuery", () => {
    const next = searchReducer(initialSearchState, {
      type: "parsed",
      data: { locality: "Bellandur", bhk: "2BHK", max_rent: 25000 },
    });
    expect(next.parsedQuery).toEqual({ locality: "Bellandur", bhk: "2BHK", max_rent: 25000 });
  });

  it("fetching with explicit sources sets all to 'fetching'", () => {
    const next = searchReducer(initialSearchState, { type: "fetching", sources: ["Reddit", "OLX"] });
    expect(next.sources).toEqual(["Reddit", "OLX"]);
    expect(next.statuses).toEqual({ Reddit: "fetching", OLX: "fetching" });
  });

  it("fetching without sources falls back to ALL_SOURCES", () => {
    const next = searchReducer(initialSearchState, { type: "fetching" });
    expect(next.sources).toEqual(ALL_SOURCES);
  });

  it("source_complete updates only the named source, preserving others", () => {
    const withFetching = searchReducer(initialSearchState, {
      type: "fetching",
      sources: ["Reddit", "OLX"],
    });
    const next = searchReducer(withFetching, { type: "source_complete", source: "Reddit", status: "ok" });
    expect(next.statuses).toEqual({ Reddit: "ok", OLX: "fetching" });
  });

  it("source_complete treats any non-'ok' status as 'error'", () => {
    const next = searchReducer(initialSearchState, {
      type: "source_complete",
      source: "NoBroker",
      status: "timeout",
    });
    expect(next.statuses.NoBroker).toBe("error");
  });

  it("brief sets the brief string", () => {
    const next = searchReducer(initialSearchState, { type: "brief", data: '{"locality":"Bellandur"}' });
    expect(next.brief).toBe('{"locality":"Bellandur"}');
  });

  it("share sets shareId, or null if omitted", () => {
    const withId = searchReducer(initialSearchState, { type: "share", id: "abc123" });
    expect(withId.shareId).toBe("abc123");
    const withoutId = searchReducer(initialSearchState, { type: "share" });
    expect(withoutId.shareId).toBeNull();
  });

  it("done sets loading false without touching other fields", () => {
    const mid = { ...initialSearchState, loading: true, brief: "x" };
    const next = searchReducer(mid, { type: "done" });
    expect(next).toEqual({ ...mid, loading: false });
  });

  it("error sets the message and stops loading", () => {
    const next = searchReducer({ ...initialSearchState, loading: true }, {
      type: "error",
      message: "Backend unreachable",
    });
    expect(next.error).toBe("Backend unreachable");
    expect(next.loading).toBe(false);
  });

  it("error with no message falls back to a generic one", () => {
    const next = searchReducer(initialSearchState, { type: "error" });
    expect(next.error).toBe("Something went wrong.");
  });
});

describe("splitSSEBuffer", () => {
  it("splits complete lines and keeps the trailing partial line as remainder", () => {
    const { lines, remainder } = splitSSEBuffer(
      'data: {"type":"parsed"}\ndata: {"type":"fetching"}\ndata: {"type":"br'
    );
    expect(lines).toEqual(['data: {"type":"parsed"}', 'data: {"type":"fetching"}']);
    expect(remainder).toBe('data: {"type":"br');
  });

  it("filters out non-'data: ' lines (SSE comments / blank keepalive lines)", () => {
    const { lines } = splitSSEBuffer(': keepalive\n\ndata: {"type":"done"}\n');
    expect(lines).toEqual(['data: {"type":"done"}']);
  });

  it("returns an empty remainder when the buffer ends on a full line", () => {
    const { lines, remainder } = splitSSEBuffer('data: {"type":"done"}\n');
    expect(lines).toEqual(['data: {"type":"done"}']);
    expect(remainder).toBe("");
  });

  it("handles an entirely empty buffer", () => {
    const { lines, remainder } = splitSSEBuffer("");
    expect(lines).toEqual([]);
    expect(remainder).toBe("");
  });
});

describe("parseSSELine", () => {
  it("parses a well-formed event", () => {
    expect(parseSSELine('data: {"type":"done"}')).toEqual({ type: "done" });
  });

  it("returns null for malformed JSON instead of throwing", () => {
    expect(parseSSELine("data: {not valid json")).toBeNull();
  });

  it("returns null for a truncated line (chunk boundary mid-event)", () => {
    expect(parseSSELine('data: {"type":"brief","data":"parti')).toBeNull();
  });
});
