import { describe, it, expect } from "vitest";
import { classifyBackendError, shouldShowColdStartHint } from "../backendErrors";

describe("classifyBackendError", () => {
  it("classifies AbortSignal.timeout's TimeoutError as a timeout", () => {
    const err = new Error("The operation was aborted due to timeout");
    err.name = "TimeoutError";
    expect(classifyBackendError(err).code).toBe("timeout");
  });

  it("classifies a message mentioning timeout even without the TimeoutError name", () => {
    expect(classifyBackendError(new Error("request timed out")).code).toBe("timeout");
  });

  it("classifies undici's 'fetch failed' as unreachable", () => {
    expect(classifyBackendError(new Error("fetch failed")).code).toBe("unreachable");
  });

  it("classifies ECONNREFUSED as unreachable", () => {
    expect(classifyBackendError(new Error("connect ECONNREFUSED 127.0.0.1:8000")).code).toBe("unreachable");
  });

  it("falls back to unknown for anything unrecognised", () => {
    expect(classifyBackendError(new Error("something bizarre")).code).toBe("unknown");
  });

  it("does not throw on non-Error values", () => {
    expect(classifyBackendError(undefined).code).toBe("unknown");
    expect(classifyBackendError("a string").code).toBe("unknown");
    expect(classifyBackendError(null).code).toBe("unknown");
  });

  it("never leaks raw internals into the user-facing message", () => {
    const leaky = ["fetch failed", "ECONNREFUSED", "127.0.0.1", "undici", "stack"];
    for (const raw of ["fetch failed", "connect ECONNREFUSED 127.0.0.1:8000", "undici error"]) {
      const { message } = classifyBackendError(new Error(raw));
      for (const token of leaky) {
        expect(message.toLowerCase()).not.toContain(token.toLowerCase());
      }
    }
  });

  it("never tells the user to check that the server is running", () => {
    // The old message did exactly this — advice aimed at a developer, not
    // at someone trying to rent a flat.
    for (const raw of ["fetch failed", "timed out", "whatever"]) {
      expect(classifyBackendError(new Error(raw)).message.toLowerCase())
        .not.toContain("server is running");
    }
  });
});

describe("shouldShowColdStartHint", () => {
  it("shows once loading has run past the threshold with no reply", () => {
    expect(shouldShowColdStartHint(true, 0, 6000)).toBe(true);
    expect(shouldShowColdStartHint(true, 0, 20000)).toBe(true);
  });

  it("stays hidden before the threshold", () => {
    expect(shouldShowColdStartHint(true, 0, 5999)).toBe(false);
    expect(shouldShowColdStartHint(true, 0, 0)).toBe(false);
  });

  it("stays hidden once the backend has replied — it's awake, just working", () => {
    expect(shouldShowColdStartHint(true, 6, 30000)).toBe(false);
  });

  it("stays hidden when not loading at all", () => {
    expect(shouldShowColdStartHint(false, 0, 60000)).toBe(false);
  });
});
