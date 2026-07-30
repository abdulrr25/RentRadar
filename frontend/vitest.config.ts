import { defineConfig, configDefaults } from "vitest/config";

export default defineConfig({
  // React 17+ automatic JSX runtime — without this, component tests fail with
  // "React is not defined" unless every file imports React explicitly, which
  // the app itself (Next.js) never has to do.
  esbuild: { jsx: "automatic" },
  test: {
    environment: "jsdom",
    globals: true,
    // e2e/ holds Playwright specs, which use a different test runner/API —
    // without this exclusion, Vitest tries to collect them too and fails
    // on the resulting duplicate @playwright/test import.
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
});
