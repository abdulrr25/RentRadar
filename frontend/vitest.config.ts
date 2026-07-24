import { defineConfig, configDefaults } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    // e2e/ holds Playwright specs, which use a different test runner/API —
    // without this exclusion, Vitest tries to collect them too and fails
    // on the resulting duplicate @playwright/test import.
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
});
