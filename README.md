# SemiDash — semiconductor news terminal

A daily news dashboard for the stocks held by the **iShares Semiconductor ETF (SOXX)**
and **VanEck Semiconductor ETF (SMH)**. It pulls company news and quotes, shows them as
tiles in a sidebar, and opens each article in an in-app reader. Refreshes automatically at
**08:00** and **13:00 Europe/London**.

## What it does

- **Ticker universe**: union of SOXX + SMH holdings. Fetched live from Finnhub at startup;
  falls back to a built-in seed list if the holdings endpoint is gated.
- **Tiles** (sidebar): each shows the ticker chip with **daily % move** (or **last close**
  when the US market is shut), a **timestamp**, the **headline**, and a **≤3-line summary**
  (Finnhub's summary, clamped to 3 lines in CSS).
- **Filter**: tick All / None or individual companies to focus the feed.
- **Reader** (right pane): article text is fetched **server-side** and rendered in-app, so it
  works even on sites that block iframes. Scroll to the bottom and the tile **greys out**
  (read state persists in SQLite). "Open original" always links out.
- **Window**: only articles from the last **7 days** (change `LOOKBACK_DAYS` in `config.py`).

## Setup

### Option A — Cloud (recommended, works from an iPad)

No computer or terminal needed. See **DEPLOY_FROM_IPAD.md** for click-by-click
instructions: upload to GitHub in the browser, connect to Render, paste your Finnhub
key, done. Render provisions a free Postgres database automatically (via `render.yaml`),
so your read-state and article history persist across restarts.

### Option B — Local (on a Mac/PC)

1. Get a free Finnhub API key: https://finnhub.io  (60 calls/min free tier is plenty)
2. Install and run:

```bash
pip install -r requirements.txt
export FINNHUB_KEY="your_key_here"      # Windows: set FINNHUB_KEY=your_key_here
uvicorn app:app --reload --port 8000
```

3. Open http://localhost:8000

Locally the app uses a SQLite file (no database setup). If a `DATABASE_URL`
environment variable is present, it uses Postgres instead — same code, either way.

On first launch it fetches immediately so the board isn't empty, then follows the
08:00 / 13:00 schedule. Use the **↻ Reload** button, or `POST /api/refresh`, to pull on demand.

## Files

| File            | Role |
|-----------------|------|
| `app.py`        | FastAPI app, routes, APScheduler jobs |
| `pipeline.py`   | Finnhub holdings/news/quotes + server-side article extraction |
| `db.py`         | SQLite storage (articles, quotes, tickers, read state) |
| `config.py`     | API key, schedule, lookback, seed ticker universe |
| `static/index.html` | Single-page React frontend (no build step) |

## Notes & limits (prototype)

- **Article extraction** uses a generic readability heuristic. Most news sites work from a
  residential IP; paywalled or bot-filtered sites fall back to a "read the original" prompt.
- **Summaries** are Finnhub's own. To swap in LLM-generated 3-line summaries later, add a
  step in `pipeline.fetch_news_and_quotes` and store into the `summary` column.
- **Storage** is a single SQLite file (`semidash.db`). Delete it to reset.
- No auth, single-user, in-memory-simple by design — it's a prototype.

## Next steps if you take it further

- LLM summarisation for tighter, consistent 3-line summaries.
- Per-sector grouping (not just per-ticker) since you mentioned tracking sectors.
- Websocket push instead of polling for near-real-time updates.
- Dockerfile + a proper process manager for deployment.
