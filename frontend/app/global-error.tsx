"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

// Catches errors thrown from the root layout itself — app/error.tsx can't,
// since it renders inside that layout. Sentry recommends this file
// explicitly; without it, root-layout crashes go unreported.
export default function GlobalError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif" }}>
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "1rem", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800 }}>Something went wrong</h1>
          <p style={{ marginTop: "0.5rem", color: "#64748b", maxWidth: "24rem" }}>
            An unexpected error interrupted the page. It's been logged.
          </p>
          <a href="/" style={{ marginTop: "1.5rem", color: "#4f46e5", fontWeight: 600, textDecoration: "none" }}>
            Back to RentRadar
          </a>
        </div>
      </body>
    </html>
  );
}
