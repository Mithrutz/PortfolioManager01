# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local investment portfolio tracker: a Flask backend (`app.py`) serving a single-file React frontend (`index.html`, no build step — React loaded via CDN `<script>` tags, UI written with `React.createElement` via the `h` alias, not JSX). Optional Google Drive sync and a PyInstaller build for a standalone Windows .exe. UI is bilingual (Romanian/English).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (dev)
python app.py
# → http://localhost:5000

# Build standalone Windows .exe (installs its own deps incl. pywebview/pyinstaller)
build_windows.bat
# → dist\PortfolioManager.exe (uses portfolio_manager.spec)
```

There is no test suite, linter, or frontend build step in this repo.

## Architecture

**Backend (`app.py`, single file, Flask)**
- `DATA_FILE` / `data_path()`: resolves `portfolio_data.json` next to `app.py` when run from source, or next to the `.exe` when frozen (PyInstaller `sys.frozen`) — this matters any time you touch file paths, since dev and packaged behavior differ.
- `load_data()` / `save_data()` / `migrate()`: the entire app state lives in one JSON file (`portfolio_data.json`) with top-level keys `cursuri` (exchange rates), `pozitii` (positions), `snapshots` (historical value points), `tranzactii` (transaction history), `next_id`. `migrate()` runs on every load to upgrade old field/category names (e.g. Romanian category names → English) — extend it when changing the data schema, don't break old files.
- `save_data()` triggers a non-blocking background Drive upload (`threading.Thread`) whenever Drive sync is enabled — keep writes going through this function rather than writing `portfolio_data.json` directly.
- **Price fetching** is a fallback chain: Stooq → Yahoo Finance (`yfinance`) → BVB (`bvb.ro` scrape via BeautifulSoup), see `get_stooq`, `get_yfinance`, `get_bvb`. Once a source works for a ticker it's cached on the position as `ticker_source` so future refreshes skip straight to it (`refresh_prices_stream`).
- `/api/refresh-prices/stream` is a Server-Sent Events endpoint (`stream_with_context`) that streams per-position progress (`start` / `progress` events) while prices are refreshed — the frontend renders live progress from this stream rather than polling.
- `DriveSync` class: hand-rolled Google Drive REST client (not the `google-api-python-client` library, deliberately, to avoid discovery-document timeouts). OAuth via `google-auth-oauthlib`; needs `credentials.json` next to the app, persists `token.json`. Only active if `credentials.json` is present (`self.enabled`).
- Other API routes: `/api/data` (GET/POST full state), `/api/snapshots` (GET/POST/DELETE), `/api/drive/status`, `/api/drive/sync`, `/api/test-ticker` (validate a ticker against the price sources), `/api/shutdown`.

**Frontend (`index.html`, single file)**
- No JSX/build tooling — components are plain functions using `React.createElement` (aliased `h`). Key components: `App` (root), `AllocChart`, `PnlChart`, `MiniDonut`.
- Talks to the backend only via the `/api/*` routes above; live price refresh consumes the SSE stream.

**Data model quirk**: `portfolio_data.json` is listed in `.gitignore` ("never commit — personal financial data") but this particular repo's own data file has historically been committed anyway (see recent commit history). Don't assume it's untracked — check `git status` before treating edits to it as safe/ignorable, and don't casually revert or overwrite it.

**Packaging**: `portfolio_manager.spec` (PyInstaller, onefile) bundles `index.html` as data and pulls in hidden imports for Flask, yfinance/pandas, and `pywebview` (native window via WebView2 on Windows — the packaged app has no console and runs in its own window, not a browser tab).
