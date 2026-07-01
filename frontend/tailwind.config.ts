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
        sans:    ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-sora)", "var(--font-inter)", "sans-serif"],
      },
      colors: {
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
      },
      boxShadow: {
        card:  "0 1px 0 rgba(15,23,42,0.04) inset, 0 8px 32px -4px rgba(15,23,42,0.1), 0 2px 8px -2px rgba(15,23,42,0.06)",
        lift:  "0 12px 40px -8px rgba(15,23,42,0.14), 0 4px 12px -4px rgba(15,23,42,0.08)",
        input: "0 1px 2px rgba(15,23,42,0.05)",
        "btn-primary": "0 1px 3px rgba(79,70,229,0.3), 0 4px 12px -2px rgba(79,70,229,0.2)",
      },
    },
  },
  plugins: [],
};

export default config;
