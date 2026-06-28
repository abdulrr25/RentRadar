import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        radar: {
          bg: "#0a0a0f",
          card: "#111118",
          border: "#1e1e2e",
          accent: "#6366f1",
          green: "#22c55e",
          red: "#ef4444",
          amber: "#f59e0b",
          muted: "#6b7280",
        },
      },
      animation: {
        pulse_slow: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
