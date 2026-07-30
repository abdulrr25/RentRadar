import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

const trackPageview = vi.fn();
const usePathname = vi.fn();

vi.mock("../../../lib/analytics", () => ({
  trackPageview: () => trackPageview(),
  track: () => {},
}));

vi.mock("next/navigation", () => ({
  usePathname: () => usePathname(),
}));

import PageviewTracker from "../PageviewTracker";

beforeEach(() => {
  trackPageview.mockClear();
  usePathname.mockReturnValue("/");
});

describe("PageviewTracker", () => {
  it("fires a pageview on mount", () => {
    render(<PageviewTracker />);
    expect(trackPageview).toHaveBeenCalledTimes(1);
  });

  it("fires again when the route changes", () => {
    const { rerender } = render(<PageviewTracker />);
    expect(trackPageview).toHaveBeenCalledTimes(1);

    usePathname.mockReturnValue("/terms");
    rerender(<PageviewTracker />);

    expect(trackPageview).toHaveBeenCalledTimes(2);
  });

  it("does not re-fire when re-rendered on the same route", () => {
    const { rerender } = render(<PageviewTracker />);
    rerender(<PageviewTracker />);
    expect(trackPageview).toHaveBeenCalledTimes(1);
  });

  it("renders nothing", () => {
    const { container } = render(<PageviewTracker />);
    expect(container.innerHTML).toBe("");
  });
});
