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
│  Anakin Wire API      Anakin Search API    │
│  · Reddit             · NoBroker           │
│  · Google News        · OLX               │
│  · Hacker News        · Housing.com        │
│       │                      │             │
│       └───────────┬──────────┘             │
│                   ▼                         │
│         Groq / Llama 3.3 70B               │
│         (synthesis → JSON brief)           │
│                   │                         │
│         SSE stream → frontend              │
└─────────────────────────────────────────────┘
```

### Data Sources

| Source | Tool | What It Provides |
|--------|------|-----------------|
| Reddit (`r/bangalore`) | Anakin Wire API | Tenant sentiment, locality reputation |
| Google News | Anakin Wire API | Recent rental market coverage |
| Hacker News | Anakin Wire API | Tech-worker housing signals |
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
│   │   ├── holocron.py  # Wire API (Reddit, Google News, HN)
│   │   └── scraper.py   # Search API (NoBroker, OLX, Housing.com)
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

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Anakin API Key](https://anakin.ai)
- [Groq API Key](https://console.groq.com) — free

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
4. Add env vars: `ANAKIN_API_KEY`, `GROQ_API_KEY`
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

After a search returns results, users can enter a phone number to get notified when a new matching listing appears — the "notify me when a 2BHK under ₹25k shows up in Bellandur" flow.

**Status: fully built, WhatsApp sending is a stub.** There is no WhatsApp Business API account wired up yet (see [whatsapp.py](backend/whatsapp.py)) — every send just logs what would have gone out, so the rest of the pipeline can be exercised end-to-end today. Swapping in a real provider (e.g. AiSensy) later only requires rewriting the body of `send_whatsapp()`.

**Storage:** SQLite (`backend/alerts.db`, git-ignored) via `aiosqlite` — `saved_searches` and `seen_listings` tables, initialised automatically on backend startup (see `db.py`). Deliberately not Postgres: zero infra to provision pre-launch. Move to a real Postgres pool if usage grows past a single instance.

**Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `POST /alerts` | Create a saved search (phone, locality, bhk, max_rent). Sends a WhatsApp confirmation request. |
| `POST /alerts/webhook` | Inbound WhatsApp message handler — a "YES" reply confirms the most recent pending search for that phone. Point your BSP's webhook here once one exists. |
| `DELETE /alerts/{id}` | Deactivate a saved search. |
| `POST /internal/run-alerts` | Checks every active, confirmed saved search for new matches and fires alerts. Requires an `X-Internal-Secret` header matching `ALERTS_INTERNAL_SECRET` — returns 503 if that env var isn't set, so it can't run unprotected by accident. Meant to be called by a scheduler (e.g. a Render Cron Job hitting this every 30–60 min), not by the frontend. |

The matching worker ([alert_worker.py](backend/alert_worker.py)) intentionally skips the LLM synthesis step used by `/search` — it calls the NoBroker/OLX/Housing.com scrapers directly and only alerts on listings with a parsed price at or under budget, keeping each run to Anakin search credits only (no Groq tokens spent on unattended background checks).

**To go live:** set `AISENSY_API_KEY` (or your chosen BSP's key) once an account and approved WhatsApp templates exist, implement the real send call in `whatsapp.py`, set `ALERTS_INTERNAL_SECRET`, and wire a Render Cron Job to call `POST /internal/run-alerts`.

---

## License

MIT © [abdulrr25](https://github.com/abdulrr25)
