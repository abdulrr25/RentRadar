import { test, expect } from "@playwright/test";

/**
 * The one true end-to-end test the audit called for: real DOM interaction
 * through a real browser, driving the actual SSE-parsing code path in
 * page.tsx/searchReducer.ts — not a unit test with a fake event object.
 *
 * The backend response is mocked at the network boundary (page.route) so
 * this never depends on or spends real Anakin/Groq credits — this is a
 * frontend rendering/interaction test, not a re-test of the already
 * extensively-tested backend pipeline.
 */

const MOCK_SOURCES = ["Reddit", "Google News", "Hacker News", "NoBroker", "OLX", "Housing.com"];

const MOCK_EVENTS = [
  { type: "parsed", data: { locality: "Bellandur", bhk: "2BHK", max_rent: 25000, city: "Bangalore", raw_query: "2BHK near Bellandur under 25000" } },
  { type: "fetching", sources: MOCK_SOURCES },
  ...MOCK_SOURCES.map((source) => ({ type: "source_complete", source, status: "ok" })),
  {
    type: "brief",
    data: JSON.stringify({
      locality: "Bellandur",
      search_summary: "2BHK rentals in Bellandur under budget",
      top_listings: [
        {
          rank: 1,
          locality_detail: "Bellandur",
          rent: 22000,
          bhk: "2BHK",
          source: "NoBroker",
          url: "https://example.com/listing",
          highlights: ["Owner direct"],
        },
      ],
      locality_scores: { safety: 8.0, overall: 7.5 },
      price_trend: "stable",
      trend_note: "Prices have been steady",
      reddit_pulse: "Generally a good area to live",
      hn_signal: "No specific signal",
      green_flags: ["Good connectivity"],
      red_flags: ["Traffic during peak hours"],
      scam_alerts: [],
      verdict: "A solid option worth considering.",
    }),
  },
  { type: "share", id: "e2etest1" },
  { type: "done" },
];

function sseBody(events: object[]): string {
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

test("search flow: type a query, brief renders, share button appears", async ({ page }) => {
  await page.route("**/api/search", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody(MOCK_EVENTS),
    })
  );

  await page.goto("/");

  await page.getByPlaceholder(/2BHK near Bellandur/i).fill("2BHK near Bellandur under 25000");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText("Scan complete")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bellandur" })).toBeVisible();
  await expect(page.getByText("₹22,000")).toBeVisible();
  await expect(page.getByText("A solid option worth considering.")).toBeVisible();

  // The shareable-link feature's whole point: a Share action must actually
  // be present once a brief with a share id has rendered.
  await expect(page.getByRole("button", { name: "Share" })).toBeVisible();
  await expect(page.getByRole("link", { name: /whatsapp/i })).toBeVisible();
});

test("empty query cannot be submitted", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Search" })).toBeDisabled();
});
