# Interrapidísimo Tracker (Refactor)

This is a refactored, modular version of your original `script.py`.

## Structure

```text
automatic/
├─ app.py                     # Orchestrator / CLI
├─ config.py                  # Settings loaded from .env (no secrets)
├─ logging_setup.py           # Logging (console + daily file)
├─ services/
│  ├─ drive_client.py         # Google Drive: latest file and download
│  ├─ sheets_client.py        # Google Sheets: sheet ops and daily report
│  └─ tracker_service.py      # Business rules: normalize, alerts, decisions
├─ utils/
│  ├─ checkpoints.py          # Save/load last processed row
│  └─ retry.py                # Backoff retry decorator (future use)
├─ web/
│  └─ inter_scraper.py        # Playwright scraper (Chromium): get_status()
└─ tests/
   └─ test_tracker_service.py # Unit tests for core business logic
```

## Requirements

- Python 3.10+
- `credentials.json` (Service Account) in the project root (not committed)

Install deps:

```bash
pip install -r requirements.txt
# Install Playwright browser binaries (one-time)
python -m playwright install chromium
```

## Environment

Create a `.env` file (no secrets):

```ini
DRIVE_FOLDER_ID=...        # Google Drive folder ID with daily Excel
SPREADSHEET_NAME=seguimiento
HEADLESS=false             # false to see the browser while debugging; set true in production
TZ=America/Bogota
DAILY_REPORT_PREFIX=Informe_
```

## Run

```bash
python app.py --start-row 2 --limit 500
```

- Status updates are batched to reduce API calls.
- Daily discrepancies are written/append to `Informe_YYYY-MM-DD` sheet.
- Terminal states (`ENTREGADO` / `DEVUELTO`) are not re-queried.
- Scraper now uses Playwright + Chromium. If site changes, enable `HEADLESS=false` and re-run to observe.

## Cron (1–2am COL)

Example (Linux cron):

```bash
0 2 * * * /bin/bash -lc 'cd /path/automatic && source venv/bin/activate && python app.py --start-row 2 >> logs/$(date +\%F).log 2>&1'
```

## Notes

- `script.py` remains in place for now; new entrypoint is `app.py`.
- The scraper uses Playwright + Chromium; adjust headless with `HEADLESS`.
- Business rules and state normalization live in `services/tracker_service.py` and are driven by JSON mappings in project root.

## Large scale (10k+ rows)

- Rows are processed sequentially and written to Sheets in batches of 200 cells to minimize API overhead.
- Terminal states are skipped to avoid unnecessary web queries.
- For higher throughput, enable concurrency and rate-limiting in a future step (design already considered).
