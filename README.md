# StatSense

Sports analytics dashboard that turns StatsBomb match data into fan-friendly insights.

## Phase 1 - Data layer

```bash
cd statsense/backend
pip install -r requirements.txt
python data_loader.py
```

This loads 5 sample matches (La Liga, Premier League, Women's World Cup) into `statsense.db`.

## Phase 2 - Insight engine (Groq)

AI insights use the [Groq API](https://console.groq.com/).

```bash
cd statsense/backend
pip install -r requirements.txt

# PowerShell
$env:GROQ_API_KEY = "your_key_here"

# Test (Messi xG + Arsenal PPDA examples from the spec)
python insight_engine.py --demo

# Offline template only (no API call)
python insight_engine.py --demo --fallback
```

Copy `.env.example` to `.env` and set `GROQ_API_KEY` if you load env vars in the FastAPI app later.

## Phase 3 - Backend API

```bash
cd statsense/backend
pip install -r requirements.txt
python data_loader.py          # if statsense.db is empty
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000/docs** for interactive API docs.

| Endpoint | Description |
|----------|-------------|
| `GET /matches` | List all matches |
| `GET /match/{match_id}` | Match stats, team benchmarks, AI summary, top performers |
| `GET /match/{match_id}/player/{player_id}` | Player stats + insight cards |
| `GET /player/{player_id}/season` | Season aggregates + trend |
| `POST /ask` | Fan Q&A (`question`, `match_id`) |

## Phase 4 - Frontend dashboard

React + Tailwind + Recharts UI. The dev server proxies `/api` → `http://127.0.0.1:8000`.

**Terminal 1 - backend:**

```bash
cd statsense/backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - frontend:**

```bash
cd statsense/frontend
npm install
npm run dev
```

Open **http://localhost:5173**

| Page | Features |
|------|----------|
| Home | Match cards (teams, score, competition, date) |
| Match dashboard | AI summary, team stat bars, top 3 performers, fan Q&A |
| Player card (slide-over) | Stats grid, insight badges, bar chart vs team avg, AI insights |

Production build: `npm run build` (set `VITE_API_URL=http://127.0.0.1:8000` if not using the dev proxy).

## Phase 5 - Bonus features

**Fan mode toggle** (nav bar): Casual · Enthusiast · Analyst - filters stats, timeline, and comparison depth.

**Timeline** (Enthusiast+): Goals, cards, subs from StatsBomb. Click an event for an AI impact explanation.

```bash
cd statsense/backend
python data_loader.py --backfill-events   # populate timeline for existing matches
```

**Player comparison** (Enthusiast+): Pick two players on the match page → side-by-side table + Groq verdict.

| Endpoint | Description |
|----------|-------------|
| `GET /match/{id}/timeline` | Key match events |
| `POST /match/{id}/compare` | `{ player_a_id, player_b_id }` |
| `POST /match/{id}/timeline/explain` | `{ event_id }` → AI insight |
