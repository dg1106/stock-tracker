# Stock Tracker — CLAUDE.md

## Project Overview

A FastAPI web app that tracks StradVision (stock code 475040) pre-IPO stock price data. It scrapes [ustockplus.com](https://www.ustockplus.com/stock/stradvision-475040) and serves a single-page dashboard with live price, order book, stats, and charts.

Deployed on **Render** (free tier) as `stradvision-tracker`.

## Architecture

```
main.py        — FastAPI app, in-memory cache, 60s background refresh loop
scraper.py     — Scrapes ustockplus.com via requests + BeautifulSoup (__NEXT_DATA__ JSON)
static/
  index.html   — Single-page frontend (vanilla JS/HTML)
render.yaml    — Render deployment config
requirements.txt
```

### Data Flow

1. On startup, `main.py` calls `scraper.get_price()` immediately, then every 60 seconds.
2. Data is stored in `_cache["data"]` (in-memory dict, no database).
3. Frontend polls `/api/price` and renders the dashboard.

### API Endpoints

- `GET /api/price` — returns cached stock data as JSON
- `HEAD /api/price` — same (for UptimeRobot health checks)
- `GET /` — serves `static/index.html`

### Scraper (`scraper.py`)

- Fetches `__NEXT_DATA__` script tag from ustockplus.com (Next.js hydration data)
- Extracts from React Query cache keyed by `(queryKey, stockCode)` tuples
- Data points: current price, prev close, change, ask/bid, today high/low/volume, 52w range, market cap, today order stats, recent 5 trades, IPO status, period charts (1m/3m/1y/3y/all)
- Stock code is hardcoded: `475040`

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# Open http://localhost:8000
```

To test the scraper directly:
```bash
python scraper.py
```

## Deployment

```bash
# Render auto-deploys on git push to master
git push origin master
```

Config is in `render.yaml`. Python 3.11, free plan.

## Key Constraints

- **No database** — all data is in-memory; restarts lose cache until next scrape.
- **SSL verification disabled** in scraper (`verify=False`) due to ustockplus.com cert issues.
- **Scraper is fragile** — depends on `__NEXT_DATA__` JSON structure of ustockplus.com. If the site changes its React Query keys or page structure, the scraper breaks.
- **Single stock only** — hardcoded to StradVision (475040). Generalizing requires refactoring `scraper.py` and the frontend.
