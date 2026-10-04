import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import RentRadarCard from "../RentRadarCard";

/**
 * Area claims gained a source + date (agent.py's `_cited`). Briefs persisted
 * before that change are replayed verbatim on /s/[id] forever, so the card
 * has to render the legacy plain-string shape as well as the new one — a
 * regression here silently breaks every share link ever sent.
 */

const CITED = {
  locality: "Bellandur",
  scam_alerts: [{
    text: "A leasing fraud was reported in Bengaluru",
    url: "https://news.example/fraud",
    source: "Google News",
    published_at: 1760000000,
    locality_specific: false,
  }],
  red_flags: [{
    text: "Rents climbing sharply",
    url: "https://news.example/rents",
    source: "Google News",
    published_at: 1760000000,
    locality_specific: true,
  }],
};

const LEGACY = {
  locality: "Bellandur",
  scam_alerts: ["A leasing fraud was reported in Bengaluru"],
  red_flags: ["Rents climbing sharply"],
};

describe("RentRadarCard claim rendering", () => {
  it("renders a cited claim with a working source link", () => {
    render(<RentRadarCard rawBrief={JSON.stringify(CITED)} />);

    expect(screen.getByText(/leasing fraud was reported/i)).toBeInTheDocument();

    const hrefs = screen
      .getAllByRole("link", { name: /google news/i })
      .map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("https://news.example/fraud");
    expect(hrefs).toContain("https://news.example/rents");

    for (const a of screen.getAllByRole("link", { name: /google news/i })) {
      expect(a).toHaveAttribute("target", "_blank");
    }
  });

  it("labels a city-wide claim so it isn't read as being about the locality", () => {
    render(<RentRadarCard rawBrief={JSON.stringify(CITED)} />);
    expect(screen.getByText(/bengaluru-wide/i)).toBeInTheDocument();
  });

  it("does not label a locality-specific claim as city-wide", () => {
    render(<RentRadarCard rawBrief={JSON.stringify({ ...CITED, scam_alerts: [] })} />);
    expect(screen.queryByText(/bengaluru-wide/i)).not.toBeInTheDocument();
  });

  it("still renders legacy string claims from briefs saved before citations", () => {
    render(<RentRadarCard rawBrief={JSON.stringify(LEGACY)} />);

    expect(screen.getByText(/leasing fraud was reported/i)).toBeInTheDocument();
    expect(screen.getByText(/rents climbing sharply/i)).toBeInTheDocument();
    // No source to link to — it must degrade quietly, not crash or show a
    // dangling "Source" link.
    expect(screen.queryByRole("link", { name: /google news/i })).not.toBeInTheDocument();
  });
});
