# RentRadar 🏠

> AI rental intelligence for Bangalore — type a plain-English query, get a live-streamed brief with top listings, locality scores, Reddit pulse, price trend, and scam alerts.

![Status](https://img.shields.io/badge/status-live-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/next.js-14-black)
![License](https://img.shields.io/badge/license-MIT-purple)

---

## What It Does

Type **"2BHK near Bellandur under ₹25,000"** and RentRadar:

1. Parses your natural language query into structured parameters
2. Fires **6 parallel data fetches** across live portals and discussion platforms
3. Synthesises everything with **Llama 3.3 70B via Groq** into a structured rental brief
4. Streams results back in real time via Server-Sent Events

**Output per search:**
- Top listings (NoBroker · OLX · Housing.com) with prices, highlights, and direct property links
- Locality scores — safety, water supply, traffic, food, public transport (1–10)
- Price trend direction (rising / stable / falling) with a one-line insight
- Reddit pulse — what Bangalore renters are saying right now
- Tech-worker signal from Hacker News
- Green flags, red flags, and scam alerts
- Plain-English verdict

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            Next.js 14 Frontend              │
│  SearchBar → SSE stream → RentRadarCard     │
└───────────────────┬─────────────────────────┘
                    │ GET /search (SSE)
┌───────────────────▼─────────────────────────┐
│              FastAPI Backend                │
│                                             │
│  parser.py → LangGraph Agent               │
│                   │                         │
│       ┌───────────┴──────────┐             │
│       ▼                      ▼             │
│  Free sentiment APIs  Anakin Search API    │
│  · Reddit (OAuth)     · NoBroker           │
│  · Google News (RSS)  · OLX               │
│  · Hacker News (HN)   · Housing.com        │
│       │                      │             │
│       └───────────┬──────────┘             │
│                   ▼                         │
│         Groq / gpt-oss-120b                │
│         (synthesis → JSON brief)           │
│                   │                         │
│         SSE stream → frontend              │
└─────────────────────────────────────────────┘
```

### Data Sources

| Source | Tool | What It Provides |
|--------|------|-----------------|
| Reddit (`r/bangalore`) | Reddit official API | Tenant sentiment, locality reputation |
| Google News | Google News RSS | Recent rental market coverage |
| Hacker News | Algolia HN Search API | Tech-worker housing signals |
| NoBroker | Anakin Search API | Owner-direct listings with prices |
| OLX | Anakin Search API | Individual rental ad pages |
| Housing.com | Anakin Search API | Broker listings with deposit info |

---

## Project Structure

```
RentRadar/
├── backend/
│   ├── main.py          # FastAPI + SSE endpoint
│   ├── agent.py         # LangGraph graph (fetch → synthesise)
│   ├── parser.py        # Natural language → structured query
│   ├── prompts.py       # System prompt + context builder with ref-map
│   ├── tools/
│   │   ├── sentiment_sources.py  # Free APIs (Reddit, Google News, HN)
│   │   └── scraper.py            # Anakin Search API (NoBroker, OLX, Housing.com)
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Main page with SSE handling
│   │   ├── layout.tsx               # Fonts + metadata
│   │   ├── globals.css              # Glassmorphism + animations
│   │   ├── api/search/route.ts      # SSE proxy to FastAPI
│   │   └── components/
│   │       ├── SearchBar.tsx        # Input with example queries
│   │       ├── HowItWorks.tsx       # Pre-search landing section
│   │       ├── RentRadarCard.tsx    # Full result brief card
│   │       ├── ListingCards.tsx     # Clickable listing cards
│   │       ├── LocalityScores.tsx   # Animated gradient score bars
│   │       └── SourceIndicators.tsx # Live source status pills
│   ├── package.json
│   ├── tailwind.config.ts
│   └── vercel.json
├── render.yaml           # Render.com backend deployment config
├── .env.example
├── .gitignore
└── README.md
```

---

## Testing & CI

**Backend** — pytest suite (79 tests) covering the query parser, price extraction/context building, the saved-search alerts store, the query cache, source-health tracking, and every API endpoint (validation, rate limits, the webhook/internal-endpoint secret guards, a stubbed-agent happy path for `/search`):

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

Tests run against an isolated DB file per test (via pytest's `tmp_path`) and reset every module-level global (rate limiter, query cache, source health) between tests, so run order never matters — each of those was a real bug caught during development, not a defensive habit.

**Frontend** — two layers, matching what each is actually good at:

```bash
cd frontend
npm test              # Vitest — unit tests for the SSE state machine (lib/searchReducer.ts)
npm run build          # required before e2e — Playwright's webServer reuses this build
npm run test:e2e       # Playwright — one real browser driving a real search end-to-end
```

The SSE event-parsing logic used to live entirely inline inside `page.tsx`'s fetch loop — the most fragile part of the app (malformed JSON, network chunks split mid-line, an abort mid-stream) with zero coverage. It's now a pure, extracted module (`lib/searchReducer.ts`) with 19 unit tests. The one Playwright spec (`e2e/search.spec.ts`) drives an actual browser through search → brief renders → share button appears, with the backend response mocked at the network boundary (`page.route`) — this tests real frontend rendering/interaction, not a re-test of the already extensively-tested backend, and never spends real Anakin/Groq credits.

[GitHub Actions](.github/workflows/ci.yml) runs all of the above — backend pytest, frontend typecheck, Vitest, build, and Playwright — on every push and PR to `master`.

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Anakin API Key](https://anakin.ai) — listing search only (NoBroker/OLX/Housing.com)
- [Groq API Key](https://console.groq.com) — free
- [Reddit app credentials](https://www.reddit.com/prefs/apps) (type: "script") — free, client-credentials only, no account password stored

### 1. Clone and configure

```bash
git clone https://github.com/abdulrr25/RentRadar.git
cd RentRadar
cp .env.example .env
```

Fill in `.env`:
```env
ANAKIN_API_KEY=your_anakin_api_key
GROQ_API_KEY=your_groq_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Start the backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check: `http://localhost:8000/health` → `{"status": "ok"}`

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## Deployment

### Backend → Render.com

1. Connect your GitHub repo on [render.com](https://render.com)
2. Select **New Web Service** → choose this repo → root directory: `backend`
3. Runtime: **Python 3**, Build: `pip install -r requirements.txt`, Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add env vars: `ANAKIN_API_KEY`, `GROQ_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
5. Deploy — note the `https://rentradar-backend.onrender.com` URL

### Frontend → Vercel

1. Import repo on [vercel.com](https://vercel.com) → root directory: `frontend`
2. Add env var: `NEXT_PUBLIC_API_URL=https://your-render-url.onrender.com`
3. Deploy

---

## Example Queries

```
2BHK near Bellandur under ₹25,000
1BHK Whitefield under ₹18,000
3BHK HSR Layout under ₹45,000
2BHK Koramangala below Rs 30000
2BHK Indiranagar under ₹35,000
```

---

## Key Technical Details

- **Ref-based URL mapping** — each search result gets a `[REF]` tag (NB1, OLX2, HS1…); the LLM cites the ref; backend maps ref→{url, source} to prevent hallucinated URLs and badge mismatches
- **Hard budget enforcement** — listings with `rent > max_rent` are stripped in Python post-LLM, regardless of LLM behaviour
- **Adaptive diversity cap** — when 2+ platforms have data, each is capped at 2 listings so no single portal dominates
- **`sources_unavailable` short-circuit** — when all sources fail (e.g. API quota), skips LLM and returns an honest error message
- **SSE streaming** — results stream progressively: `parsed` → `fetching` → `source_complete` (×6) → `brief` → `done`

---

## SSE Event Reference

| Event | Payload | When |
|-------|---------|------|
| `parsed` | `{locality, bhk, max_rent}` | Immediately after parse |
| `fetching` | `[source names]` | Before parallel fetch |
| `source_complete` | `{source, status}` | As each of 6 finishes |
| `brief` | Full JSON brief | After synthesis |
| `done` | — | Stream end |
| `error` | Error message | On pipeline failure |

---

## Feedback

A floating feedback widget (bottom-right of every page) lets users send a 👍/👎 rating with an optional comment. Submissions go through `POST /api/feedback` (Next.js) → `POST /feedback` (FastAPI), which appends each entry as a JSON line to `backend/feedback.jsonl` — no database required. That file is git-ignored and lives on local/ephemeral disk, so on Render it resets on redeploy; treat it as a lightweight local log, not durable storage.

---

## Saved-search alerts

After a search returns results, users can subscribe to be notified when a new matching listing appears — the "notify me when a 2BHK under ₹25k shows up in Bellandur" flow. Three channels, chosen deliberately because **none of them require a WhatsApp Business API account** (no GST/business verification, no dedicated phone number):

| Channel | Opt-in flow | Setup to go live |
|---|---|---|
| **Telegram** | Deep link (`t.me/YourBot?start=<token>`) opens the bot; a `/start` message confirms | Message `@BotFather` → `/newbot` (~2 min, free, no business verification) → set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` |
| **Web Push** | Browser's native permission prompt; subscribing IS the confirmation, no extra step | Zero external account — generate a keypair with `python -m channels.webpush` (from `backend/`), set `VAPID_PRIVATE_KEY` + `VAPID_SUBJECT` server-side and `NEXT_PUBLIC_VAPID_PUBLIC_KEY` on the frontend |
| **Email** | Confirmation link sent to the address; clicking it confirms | Sign up at [resend.com](https://resend.com) (no GST needed), set `RESEND_API_KEY` |

Any channel without its env vars set falls back to a logging stub (see `backend/channels/`), so the whole pipeline — signup, matching, dedup — is testable end-to-end regardless of which channels are actually live.

**Storage:** libSQL via `libsql_client` — `saved_searches` (with `channel`/`target`/`confirm_token` columns covering all three flows), `seen_listings`, and `briefs` (for shareable links), schema initialised automatically on backend startup (see `db.py`). Same client works against either a local file (`DATABASE_URL` unset — zero setup for local dev, defaults to `backend/alerts.db`) or a hosted [Turso](https://turso.tech) database (`DATABASE_URL=libsql://...` + `DATABASE_AUTH_TOKEN`) in production. **Turso in production is not optional** — Render's free-tier disk is wiped on every redeploy, so a local file there means every confirmed alert and every shared link disappears the next time you ship a fix. Turso's free tier needs no GST/business verification and doesn't expire.

**Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `POST /alerts` | Create a saved search on one of `telegram` / `webpush` / `email`. Response shape differs per channel — see `main.py`'s `AlertRequest` validator. |
| `POST /alerts/telegram/webhook` | Inbound Telegram update; a `/start <token>` message confirms. Requires Telegram's own `X-Telegram-Bot-Api-Secret-Token` header to match `TELEGRAM_WEBHOOK_SECRET` (set via Telegram's `setWebhook` `secret_token` param) — returns 503 if unset. |
| `GET /alerts/confirm/{token}` | Email confirmation link target — renders a simple HTML success/failure page. |
| `DELETE /alerts/{id}` | Deactivate a saved search. |
| `POST /internal/run-alerts` | Checks every active, confirmed saved search for new matches and fires alerts. Requires an `X-Internal-Secret` header matching `ALERTS_INTERNAL_SECRET` — returns 503 if that env var isn't set. Meant to be called by a scheduler (e.g. a Render Cron Job hitting this every 30–60 min), not by the frontend. |

The matching worker ([alert_worker.py](backend/alert_worker.py)) intentionally skips the LLM synthesis step used by `/search` — it calls the NoBroker/OLX/Housing.com scrapers directly and only alerts on listings with a parsed price at or under budget, keeping each run to Anakin search credits only (no Groq tokens spent on unattended background checks).

---

## Security & Hardening

A few things worth knowing if you're deploying this for real users, not just local dev:

- **CORS is scoped to this project's own domains** — `http://localhost:3000` for dev, plus a regex matching only `rentradar*.vercel.app` (Vercel's preview-deployment naming convention) for production. Add any custom domain via the comma-separated `EXTRA_ORIGINS` env var. Earlier this allowed *any* `*.vercel.app` or `*.onrender.com` app with credentials — that's been tightened.
- **`/docs`, `/redoc`, and `/openapi.json` are disabled.** This API is only ever called by RentRadar's own frontend, not third parties, so a public schema is pure reconnaissance for an attacker.
- **Rate limiting** via `slowapi`, in-memory (fine for a single instance — move to a Redis-backed store via `Limiter(storage_uri=...)` if this ever scales past one): `/search` 10/10min, `/alerts` create 5/hour, `/feedback` 20/hour, `/alerts/telegram/webhook` 60/min per IP.
- **Every request body field has a length/range cap** (`SearchRequest.query`, `AlertRequest.locality`/`bhk`/`max_rent`/`target`, `FeedbackRequest.message`/`query`) — rejected at validation time, not accepted then truncated, so oversized payloads never reach Anakin/Groq calls that cost real money.
- **`/alerts/telegram/webhook` requires Telegram's own signature** — `X-Telegram-Bot-Api-Secret-Token` must match `TELEGRAM_WEBHOOK_SECRET`, which Telegram itself echoes back on every call once set via `setWebhook`'s `secret_token` param — not a static placeholder like an earlier WhatsApp-based design would have needed. Email and web push don't need an equivalent: email confirmation is protected by an unguessable per-search token, and web push confirmation is an immediate browser permission grant with no separate step to spoof.
- **Dependency scan**: `pip-audit` and `npm audit` were run against this repo. Next.js was bumped to 14.2.35 (patches a critical middleware auth-bypass CVE, safe within the same minor version). Some Starlette and Next.js CVEs remain unpatched by design — they require a FastAPI/Next major version bump and don't apply to how this app actually uses those frameworks (no file uploads, no class-based endpoints, no `next/image`, no middleware, no WebSockets). Worth re-checking `pip-audit` / `npm audit` before a real launch, since that calculus can change as the app grows.

---

## Observability

**Error tracking** via the Sentry SDKs (`sentry-sdk[fastapi]` on the backend, `@sentry/nextjs` on the frontend), pointed at [GlitchTip](https://glitchtip.com) rather than Sentry itself — GlitchTip is open-source and speaks the same ingestion protocol, so the SDK code is unchanged, but its hosted free tier is permanent (Sentry's is a 14-day trial). No-op until `SENTRY_DSN`/`NEXT_PUBLIC_SENTRY_DSN` are set, same stubbed-by-default pattern as every alert channel. Without this wired up, the only way to notice an outage (e.g. Anakin's search-credit balance hitting zero, which has actually happened during this project's own development) was reading server logs after a user complained.

Worth knowing: adding the SDK to the frontend grew the shared JS bundle from ~87 KB to ~164 KB First Load JS — a real cost, not a rounding error, and the tradeoff for actually knowing when production breaks rather than finding out from a user.

`SENTRY_ORG`/`SENTRY_PROJECT`/`SENTRY_AUTH_TOKEN` are optional on top of the DSN — they only enable build-time source map upload for cleaner stack traces; the build succeeds without them either way.

**Proactive status banner** — `backend/source_health.py` tracks whether the last real search had every data source fail (Anakin credits exhausted, network down, etc.) and `GET /health` reports it. The frontend polls this every 60s and shows a dismissible banner *before* anyone even searches, rather than only after they've typed a query and waited. Deliberately does not proactively ping Anakin to check status — that would cost real search credits just to answer "are we healthy," which would make the exact problem this exists to catch worse. This means a fresh restart assumes healthy until the first real search proves otherwise — a decision made for zero added cost, not an oversight.

**Search caching** — `backend/query_cache.py` is a 15-minute in-memory cache keyed on normalized `(locality, bhk, max_rent)`. Two identical searches within that window mean the second one skips Anakin and Groq entirely and replays the first's result — verified live: a repeat search dropped from ~9.3s to ~0.17s with zero additional Anakin/Groq HTTP calls in the logs. Only genuinely successful briefs are ever cached — `sources_unavailable` and `synthesis_failed` results are never cached, since caching a failure would keep serving a stale outage message for the full 15 minutes even after Anakin recovers, directly undermining `source_health.py`'s recovery detection above.

**Product analytics** — `frontend/lib/analytics.ts`, no-op until `NEXT_PUBLIC_UMAMI_WEBSITE_ID` is set. Wired to [Umami](https://umami.is) specifically: genuinely open-source (MIT, self-hostable for free on a cheap VPS), and its Cloud tier is a real permanent free plan — not a 14-day trial. Tracks `search_submitted`, `brief_rendered`, `alert_channel_clicked` (which of Telegram/Browser/Email gets picked), and `share_clicked` (native share sheet, clipboard copy, or the direct WhatsApp link, tracked separately). No client SDK — a plain `fetch` POST to Umami's `/api/send` — so this is zero bundle cost whether or not it's configured, confirmed via build output rather than assumed.

---

## License

MIT © [abdulrr25](https://github.com/abdulrr25)
