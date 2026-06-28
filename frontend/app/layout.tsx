import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RentRadar — Bangalore Rental Intelligence",
  description:
    "AI-powered rental intelligence for Bangalore. Find your flat instantly with live market data, Reddit pulse, and scam alerts.",
  openGraph: {
    title: "RentRadar",
    description: "Find your Bangalore flat. Instantly.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0a0a0f] text-slate-200 antialiased">
        {children}
      </body>
    </html>
  );
}
