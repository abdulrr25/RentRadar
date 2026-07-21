import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms & Conditions — RentRadar",
  description: "Terms and conditions for using RentRadar's AI rental intelligence service.",
};

const LAST_UPDATED = "21 July 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="py-6">
      <h2 className="font-display text-lg font-bold text-slate-900">{title}</h2>
      <div className="mt-2.5 space-y-3 text-sm leading-relaxed text-slate-600">{children}</div>
    </section>
  );
}

export default function TermsPage() {
  return (
    <div className="relative min-h-screen">
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200" style={{ boxShadow: "0 1px 4px rgba(15,23,42,0.06)" }}>
        <div className="mx-auto max-w-3xl px-4 sm:px-6 h-14 sm:h-16 flex items-center">
          <a href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600" style={{ boxShadow: "0 2px 8px rgba(79,70,229,0.35)" }}>
              <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
              </svg>
            </span>
            <span className="font-display text-[17px] font-bold tracking-tight text-slate-900">
              Rent<span className="gradient-text">Radar</span>
            </span>
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 sm:px-6 py-12 sm:py-16">
        <p className="badge">Legal</p>
        <h1 className="mt-4 font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
          Terms &amp; Conditions
        </h1>
        <p className="mt-3 text-sm text-slate-500">Last updated: {LAST_UPDATED}</p>

        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          RentRadar is an independent, informational tool. It is <strong>not a broker, landlord, or listing platform</strong>,
          and it is not affiliated with NoBroker, OLX, Housing.com, Reddit, or any other third-party service referenced below.
        </div>

        <div className="divide-y divide-slate-200">
          <Section title="1. Acceptance of terms">
            <p>
              By accessing or using RentRadar (the &ldquo;Service&rdquo;), you agree to be bound by these Terms &amp;
              Conditions. If you do not agree, please do not use the Service. We may update these terms from time to
              time; continued use after changes take effect constitutes acceptance of the revised terms.
            </p>
          </Section>

          <Section title="2. What RentRadar does">
            <p>
              RentRadar accepts a natural-language rental query, retrieves publicly available information from
              third-party sources (including NoBroker, OLX, Housing.com, Reddit, Google News, and Hacker News), and
              uses a large language model (Llama 3.3 70B via Groq) to synthesise that information into a summarised
              &ldquo;brief&rdquo; — including listings, locality scores, price trends, and flagged risks.
            </p>
            <p>
              This output is <strong>AI-generated and derived from third-party data we do not control</strong>. It may
              be incomplete, outdated, or inaccurate. It is provided for informational convenience only and does not
              constitute a verified listing, a guarantee of availability or price, or professional real-estate advice.
            </p>
          </Section>

          <Section title="3. No guarantee of accuracy">
            <p>
              Prices, availability, locality scores, &ldquo;green/red flags&rdquo;, and scam alerts shown by the
              Service are best-effort estimates generated from scraped snippets and community sentiment (Reddit,
              Hacker News, news coverage). They are not verified against the actual property, landlord, or listing
              platform. Locality scores in particular reflect what people say online, not objective measurement, and
              may skew toward neighbourhoods and demographics more active in those online communities.
            </p>
            <p>
              Always independently verify any listing — including price, ownership, and legitimacy — directly with
              the source platform or property owner before making any payment or commitment.
            </p>
          </Section>

          <Section title="4. No liability for third-party transactions">
            <p>
              RentRadar does not participate in, broker, or process any rental transaction. Any agreement,
              payment, deposit, or communication between you and a landlord, broker, or platform found through the
              Service is solely between you and that party. We are not responsible for losses, disputes, fraud, or
              scams arising from listings surfaced by the Service, including where our &ldquo;scam alerts&rdquo;
              feature fails to flag a fraudulent listing or incorrectly flags a legitimate one.
            </p>
          </Section>

          <Section title="5. Acceptable use">
            <p>You agree not to use the Service to:</p>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Scrape, reproduce, or redistribute Service output at scale for a competing product</li>
              <li>Submit queries designed to overload, abuse, or reverse-engineer the underlying data pipeline</li>
              <li>Use the Service for any unlawful purpose, including harassment of listing owners or brokers</li>
            </ul>
          </Section>

          <Section title="6. Feedback and contact information">
            <p>
              If you submit feedback through the Service (a rating and optional comment), we store it to improve
              the product. If future features (such as saved-search alerts) request a phone number for WhatsApp
              notifications, that number is used solely to deliver the alerts you opt into, and you may opt out
              at any time. We do not sell personal data to third parties.
            </p>
          </Section>

          <Section title="7. Service availability">
            <p>
              The Service depends on third-party APIs (Anakin, Groq) that may be rate-limited, temporarily
              unavailable, or discontinued. We do not guarantee uninterrupted availability and may modify, suspend,
              or discontinue any part of the Service at any time without prior notice.
            </p>
          </Section>

          <Section title="8. Intellectual property">
            <p>
              The RentRadar name, interface, and underlying code are our property or used under licence. Listing
              content, images, and data belong to their respective source platforms and rights holders; RentRadar
              claims no ownership over third-party content it summarises.
            </p>
          </Section>

          <Section title="9. Limitation of liability">
            <p>
              The Service is provided &ldquo;as is&rdquo; without warranties of any kind, express or implied. To the
              maximum extent permitted by law, RentRadar and its operator shall not be liable for any indirect,
              incidental, or consequential damages — including financial loss from a scam listing, a missed
              rental opportunity, or reliance on an inaccurate locality score — arising from use of the Service.
            </p>
          </Section>

          <Section title="10. Governing law">
            <p>
              These terms are governed by the laws of India. Any disputes arising from use of the Service shall be
              subject to the exclusive jurisdiction of the courts in Bengaluru, Karnataka.
            </p>
          </Section>

          <Section title="11. Contact">
            <p>
              Questions about these terms can be raised via the feedback widget on the Service, or through the
              project&rsquo;s{" "}
              <a href="https://github.com/abdulrr25/RentRadar" target="_blank" rel="noopener noreferrer" className="font-medium text-brand-600 hover:text-brand-700">
                GitHub repository
              </a>.
            </p>
          </Section>
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 py-8 text-xs text-slate-500">
          <a href="/" className="font-medium text-brand-600 hover:text-brand-700">&larr; Back to RentRadar</a>
        </div>
      </footer>
    </div>
  );
}
