import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
  variable: "--font-sora",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RentRadar — AI Rental Intelligence for Bangalore",
  description:
    "Find your Bangalore flat instantly. RentRadar scans NoBroker, OLX, Housing.com, Reddit and news in real time to surface ranked listings, locality scores, price trends and scam alerts.",
  keywords: ["Bangalore rent", "flat for rent Bangalore", "rental intelligence", "NoBroker", "Housing.com", "AI rental search"],
  openGraph: {
    title: "RentRadar — AI Rental Intelligence for Bangalore",
    description: "Find your Bangalore flat. Instantly.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${sora.variable}`}>
      <body className="min-h-screen bg-[#f7f8fb] text-slate-900 font-sans antialiased selection:bg-indigo-100 selection:text-indigo-900">
        {children}
      </body>
    </html>
  );
}
