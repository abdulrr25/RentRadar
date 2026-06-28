import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-sora)", "var(--font-inter)", "sans-serif"],
      },
      colors: {
        radar: {
          bg: "#07070b",
          card: "#0c0c12",
          border: "#1e1e2e",
          accent: "#6366f1",
          accent2: "#8b5cf6",
          green: "#22c55e",
          red: "#ef4444",
          amber: "#f59e0b",
          muted: "#6b7280",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(99,102,241,0.25), 0 8px 40px -8px rgba(99,102,241,0.45)",
        "glow-sm": "0 0 24px -6px rgba(99,102,241,0.4)",
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 60px -20px rgba(0,0,0,0.7)",
        lift: "0 24px 60px -24px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.06)",
      },
      animation: {
        pulse_slow: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
