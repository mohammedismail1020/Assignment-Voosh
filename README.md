# Assignment-Voosh
# ETL Data Pipeline: Fake Store API to SQLite Dashboard

## Overview
This project implements a simple, robust ETL (Extract, Transform, Load) pipeline using Python to fetch e-commerce product data from the Fake Store API, transform it (cleaning, filtering, and enriching with calculations like INR prices), store it in a local SQLite database, monitor runs with logging and status tracking, and visualize results via a static HTML dashboard. It's designed for local development, rerunnable without duplicates, and handles common failures like timeouts or API errors.

### Why Fake Store API?
- **Free & No Key Required**: Public endpoint (`https://fakestoreapi.com/products`) returns ~20 fake JSON products (titles, prices, descriptions, categories, ratings) – ideal for testing without auth hassles.
- **Reliable for Demo**: Static data ensures consistent results; mimics real e-commerce (e.g., clothing, electronics) for transformation examples like currency conversion.
- **Alternatives Considered**: Could swap for CoinGecko (crypto) or OpenWeatherMap (weather), but this keeps it simple and focused on product data.

## Local Setup & Running

### Prerequisites
- **Python 3.8+**: Download from [python.org](https://python.org). Verify: `python --version`.
- **Code Editor**: VS Code recommended (free at [code.visualstudio.com](https://code.visualstudio.com)).
- **No External Services**: Runs fully offline after initial API fetch; SQLite is built-in.

### Dependencies
Install via pip (run in your project folder):
```
pip install requests
```
- `requests`: For HTTP API calls.
- Built-ins: `json`, `time`, `sqlite3`, `logging`, `datetime` (no install needed).

No environment variables required (hardcoded API URL; for production, add via `.env`).

### Project Structure
```
api-fetcher/
├── etl_pipeline_with_monitoring.py  # Main ETL script (fetch → transform → store + monitor)
├── dashboard.html                    # Static HTML/JS dashboard with Chart.js
├── view_db.py                        # Optional: Quick DB query script
├── pipeline.log                      # Auto-generated: Full run logs
├── error.log                         # Auto-generated: Errors only
└── products.db                       # Auto-generated: SQLite DB with data & logs table
```

### Steps to Run
1. **Clone/Open Project**:
   - Download this repo or create a folder (`mkdir api-fetcher; cd api-fetcher`).
   - Copy `etl_pipeline_with_monitoring.py` and `dashboard.html` into it.

2. **Run the Pipeline**:
   - Open terminal in folder (VS Code: Ctrl + `).
   - Execute:
     ```
     python etl_pipeline_with_monitoring.py
     ```
   - **First Run**: Fetches 20 products → Filters/transforms to ~7 → Stores in `products.db`. Outputs: "Pipeline Status: SUCCESS".
   - **Reruns**: Updates existing records (no duplicates); logs each attempt.
   - Expected Time: <5s. Check `pipeline.log` for details.

3. **View Data**:
   - Run query script: `python view_db.py` (dumps all rows).
   - Or use VS Code extension: Install "SQLite" → Ctrl+Shift+P → "SQLite: Open Database" → Select `products.db`.

4. **Launch Dashboard**:
   - Open `dashboard.html` in browser (double-click or VS Code Live Server extension).
   - Shows: Stats cards, product table, bar chart (USD vs. INR prices).
   - Static data embedded (from your DB); refresh via rerun + manual JSON update.

5. **Monitor Runs**:
   - Check `pipeline.log` / `error.log` for traces.
   - Query DB logs: Add to `view_db.py`: `cursor.execute('SELECT * FROM logs ORDER BY run_id DESC LIMIT 5')`.
   - On failure (e.g., offline): "Pipeline Status: FAILED" + email alert (uncomment in script).

**Troubleshooting**:
- `ModuleNotFoundError: requests`: Run `pip install requests`.
- DB Empty: Rerun pipeline.
- Windows PATH Issues: Use `python -m pip install requests`.

## How the Pipeline Works
The script chains ETL + monitoring in a single, idempotent run:

1. **Extract (Fetch)**: `fetch_products()` hits API with retries (3x, exponential backoff) for timeouts/HTTP errors. Cleans basics (e.g., defaults missing fields). Logs attempts.
2. **Transform**: `transform_products()` renames keys (e.g., `title` → `name`), filters (price ≥$50, rating ≥3.0), adds calcs (INR price = USD * 83; `is_expensive` flag; rating-adjusted value). Logs filters.
3. **Load (Store)**: `store_to_db()` upserts to `products` table (SQLite schema auto-creates). Uses `INSERT OR REPLACE` on `product_id` for reruns. Creates `logs` table for run history.
4. **Monitor**: Logs to files (`pipeline.log` / `error.log`) + DB (`logs` table with timestamp/status/message). Prints final "Status: OK/FAILED". Optional: Gmail alert on failure.
5. **Display**: Static `dashboard.html` embeds sample data (table + Chart.js bar graph). For live: Query DB → Export JSON → Update array.

**DB Schema** (products table):
```sql
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price_usd REAL NOT NULL,
    desc TEXT,
    category_norm TEXT,
    image_url TEXT,
    avg_rating REAL,
    review_count INTEGER,
    price_inr REAL,
    is_expensive BOOLEAN,
    total_value_inr REAL
);
```
Logs table: `run_id` (auto), `timestamp`, `status`, `message`.

**Sample Flow Output**:
```
2025-10-29 12:00:00 - INFO - Pipeline started.
... (fetch: 20 raw)
... (transform: 7 kept)
... (store: Updated 7, Total: 7)
Pipeline Status: SUCCESS
```

## Production Improvements & Scaling
This is local/dev-ready; for prod:

- **Scheduling**: Use cron/Airflow for daily runs (e.g., `0 2 * * * python etl_pipeline.py`).
- **Error Handling**: Integrate Sentry/Slack webhooks for alerts (replace email). Add metrics (e.g., Prometheus for run duration).
- **Scaling Data**: Paginate API (loop `?limit=100&page={i}`); switch to PostgreSQL (Neon free tier) for concurrency. Use Pandas for large transforms.
- **Security/Config**: `.env` for API keys/rates (python-dotenv). Validate inputs (e.g., Pydantic schemas).
- **Dynamic Dashboard**: Flask/FastAPI backend querying DB; host on Vercel. Add filters (e.g., React frontend).
- **CI/CD**: GitHub Actions to test/run on push; Dockerize for portability.
- **Exchange Rates**: Fetch live from exchangerate-api.com in transform (free tier).
- **Testing**: Unit tests (pytest) for functions; mock API with responses lib.

## Dashboard
- **Live Demo**: [View on GitHub Pages](https://yourusername.github.io/api-fetcher/dashboard.html) (deploy via repo settings).
- **Screenshots**: See `/screenshots/` folder (table view, chart, stats).
- **Tech**: Vanilla HTML/JS + Chart.js (CDN). Embed your DB data as JSON array.

## License & Contact
MIT License. Built for learning; questions? Open an issue or email [mohammedismail766073@gmail.com].
