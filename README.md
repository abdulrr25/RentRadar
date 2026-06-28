# RentRadar 🏠

> AI-powered rental intelligence for Bangalore. Type a query, get a live-streamed brief — top listings, locality scores, Reddit pulse, price trends, and scam alerts.

![RentRadar](https://img.shields.io/badge/status-active-brightgreen) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![Next.js](https://img.shields.io/badge/next.js-14-black) ![License](https://img.shields.io/badge/license-MIT-purple)

---

## What It Does

Type something like **"2BHK near Bellandur under ₹25,000"** and RentRadar:

1. Parses your natural language query into structured params
2. Fires **7 parallel data fetches** across live sources
3. Synthesizes everything via **Claude Sonnet** into a structured rental brief
4. Streams the results back in real time via SSE

**Output includes:** top listings with prices, locality scores (safety / water / traffic / food / transport), Reddit pulse, tech-worker signals from HN, price trend direction, green flags, red flags, scam alerts, and a plain-English verdict.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              Next.js 14 Frontend              │
│   SearchBar → SSE stream → RentRadarCard      │
└────────────────────┬─────────────────────────┘
                     │ POST /api/search (SSE)
┌────────────────────▼─────────────────────────┐
│              FastAPI Backend                  │
│                                               │
│  parser.py ──► LangGraph Agent               │
│                    │                          │
│          ┌─────────┴──────────┐              │
│          ▼                    ▼              │
│   Wire (Holocron)    Universal Scraper       │
│  reddit.search        NoBroker              │
│  google_trends        MagicBricks           │
│  hackernews           Housing.com           │
│  twitter.search                             │
│          │                    │              │
│          └─────────┬──────────┘              │
│                    ▼                          │
│            Claude Sonnet (synthesis)          │
│                    │                          │
│            SSE events → frontend             │
└──────────────────────────────────────────────┘
```

### Three Anakin Tools Used

| Tool | Endpoint | Used For |
|------|----------|----------|
| **Wire (Holocron)** | `POST /v1/holocron/task` | Reddit, Google Trends, Hacker News, Twitter/X |
| **Universal Scraper** | `POST /v1/scrape` | NoBroker, MagicBricks, Housing.com (JS-rendered) |
| **Anakin MCP Server** | `@anakin-io/mcp` | Native tool access inside Claude Code during dev |

---

## Project Structure

```
rent-radar/
├── backend/
│   ├── main.py             # FastAPI + SSE endpoint
│   ├── agent.py            # LangGraph graph (fetch → synthesis)
│   ├── parser.py           # NL query → structured params
│   ├── prompts.py          # Claude synthesis prompt + context builder
│   ├── tools/
│   │   ├── holocron.py     # Wire (Holocron) calls
│   │   └── scraper.py      # Universal Scraper calls
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                    # Main page with SSE handling
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   ├── api/search/route.ts         # SSE proxy route
│   │   └── components/
│   │       ├── SearchBar.tsx           # Input with example queries
│   │       ├── RentRadarCard.tsx       # Full result brief card
│   │       ├── LocalityScores.tsx      # Animated score bars
│   │       ├── ListingCards.tsx        # Top listings
│   │       └── SourceIndicators.tsx    # Live source status pills
│   ├── package.json
│   ├── tailwind.config.ts
│   └── next.config.js
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Anakin API Key](https://anakin.ai) — for Wire (Holocron) + Universal Scraper
- [Anthropic API Key](https://console.anthropic.com) — for Claude Sonnet synthesis

---

## Setup

### 1. Clone & configure environment

```bash
git clone https://github.com/abdulrr25/RentRadar.git
cd RentRadar
cp .env.example .env
```

Edit `.env`:
```env
ANAKIN_API_KEY=your_anakin_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Backend

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

Verify: `http://localhost:8000/health` should return `{"status": "ok"}`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## MCP Setup (Development Tooling)

The Anakin MCP server exposes Wire and Universal Scraper as native tools inside Claude Code and Cursor, useful during development.

```bash
# Install globally
npm install -g @anakin-io/mcp

# Initialize — auto-configures Claude Code, Cursor, etc.
npx -y @anakin-io/mcp init --all
# Enter your ANAKIN_API_KEY when prompted
```

> **Note:** The MCP server is for development tooling only. The production app uses direct HTTP calls via `httpx` — no MCP runtime dependency.

---

## Usage Examples

```
2BHK near Bellandur under ₹25,000
1BHK Whitefield under ₹18,000
3BHK HSR Layout under ₹45,000
2BHK Koramangala below Rs 30000
```

Supported localities: Bellandur, Koramangala, Indiranagar, HSR Layout, Whitefield, Electronic City, Marathahalli, BTM Layout, Sarjapur, Hebbal, Yelahanka, Jayanagar, JP Nagar, and more.

---

## SSE Event Stream

The `/search` endpoint streams the following events:

| Event | Payload | Timing |
|-------|---------|--------|
| `parsed` | Structured query params | Immediately |
| `fetching` | List of 7 source names | Before fetch starts |
| `source_complete` | Per-source `{source, status}` | As each finishes |
| `brief` | Full Claude JSON synthesis | After all fetches + synthesis |
| `done` | — | Stream end |
| `error` | Error message | On pipeline failure |

---

## Error Handling

- Every data fetch is independently wrapped in `try/except` — a single timeout never kills the pipeline
- If NoBroker/MagicBricks/Housing.com times out → synthesis continues on remaining sources
- If ALL scrapers fail → synthesis still runs on Wire (Reddit, Trends, HN, Twitter) data
- If Claude returns malformed JSON → frontend shows a raw text fallback card
- If `ANAKIN_API_KEY` is missing → `/health` returns `{"status": "degraded", "missing_env": [...]}`

---

## License

MIT © [abdulrr25](https://github.com/abdulrr25)
