"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { trackPageview } from "../../lib/analytics";

/**
 * Fires a pageview on first load and on every client-side route change
 * (/, /s/{id}, /terms). Without this, Umami records only custom events —
 * which means a visitor who lands and leaves without searching is counted
 * as nobody, and "how many people reached the site" is unanswerable.
 *
 * Renders nothing; a true no-op when Umami isn't configured.
 */
export default function PageviewTracker() {
  const pathname = usePathname();

  useEffect(() => {
    trackPageview();
  }, [pathname]);

  return null;
}
