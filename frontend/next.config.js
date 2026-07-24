const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {};

// withSentryConfig is safe to apply even without a DSN configured — it only
// affects build-time source map upload / error wrapping, and silently
// no-ops the parts that need an auth token when SENTRY_AUTH_TOKEN is unset.
module.exports = withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
  widenClientFileUpload: true,
  webpack: {
    removeDebugLogging: true,
    automaticVercelMonitors: false,
  },
});
