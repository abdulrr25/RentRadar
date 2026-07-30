import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * analytics.ts reads NEXT_PUBLIC_UMAMI_WEBSITE_ID into a module-level const
 * at import time, so each test must stub the env BEFORE importing it.
 */
async function loadAnalytics(websiteId?: string) {
  vi.resetModules();
  if (websiteId === undefined) {
    vi.stubEnv("NEXT_PUBLIC_UMAMI_WEBSITE_ID", "");
  } else {
    vi.stubEnv("NEXT_PUBLIC_UMAMI_WEBSITE_ID", websiteId);
  }
  return import("../analytics");
}

function mockFetch() {
  const fn = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => {
  Object.defineProperty(document, "referrer", { value: "https://google.com", configurable: true });
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("trackPageview", () => {
  it("sends a payload with NO name field — this is what Umami counts as a pageview", async () => {
    const f = mockFetch();
    const { trackPageview } = await loadAnalytics("site-abc");

    trackPageview();

    expect(f).toHaveBeenCalledTimes(1);
    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.type).toBe("event");
    expect(body.payload.website).toBe("site-abc");
    // The whole point: a `name` would make Umami classify this as a custom
    // event instead of a pageview, and visitor counts would stay at zero.
    expect(body.payload).not.toHaveProperty("name");
  });

  it("includes referrer so traffic sources are attributable", async () => {
    const f = mockFetch();
    const { trackPageview } = await loadAnalytics("site-abc");

    trackPageview();

    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.payload.referrer).toBe("https://google.com");
  });

  it("is a true no-op when the website id is not configured", async () => {
    const f = mockFetch();
    const { trackPageview } = await loadAnalytics(undefined);

    trackPageview();

    expect(f).not.toHaveBeenCalled();
  });

  it("never throws when the network request rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const { trackPageview } = await loadAnalytics("site-abc");

    expect(() => trackPageview()).not.toThrow();
  });
});

describe("track (custom events)", () => {
  it("sends a payload WITH a name field", async () => {
    const f = mockFetch();
    const { track } = await loadAnalytics("site-abc");

    track("search_submitted", { locality: "Bellandur" });

    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.payload.name).toBe("search_submitted");
    expect(body.payload.data).toEqual({ locality: "Bellandur" });
  });

  it("is a true no-op when the website id is not configured", async () => {
    const f = mockFetch();
    const { track } = await loadAnalytics(undefined);

    track("search_submitted");

    expect(f).not.toHaveBeenCalled();
  });
});
