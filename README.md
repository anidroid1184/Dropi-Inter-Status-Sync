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
- STATUS TRACKING se llena únicamente con el resultado del scraping (Interrapidísimo), no con el estado de DROPi.
- Scraper usa Playwright + Chromium. Si el sitio cambia, ejecuta con `HEADLESS=false` para observar.

## Deploy on Linux (server)

Steps to prepare and schedule the daily run with cron.

1) Clone and setup

```bash
cd /opt
git clone <repo_url> automatic
cd automatic
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
# Playwright browsers (one-time)
python -m playwright install chromium
```

2) Configure environment

Create `.env` in project root:

```ini
SPREADSHEET_NAME=seguimiento
TZ=America/Bogota
DAILY_REPORT_PREFIX=Informe_
# If exporting/uploading the XLSX to Drive:
DRIVE_FOLER_INDIVIDUAL_FILE=<folder_id_in_shared_drive_or_use_delegation>
```

Place `credentials.json` (Service Account) in the project root.

3) Run full flow manually

```bash
chmod +x scripts/run_all.sh
./scripts/run_all.sh
# Optional tuning via env vars before the command:
START_ROW=2 BATCH_SIZE=1000 MAX_CONCURRENCY=3 RPS=1.0 RETRIES=2 TIMEOUT_MS=45000 SLEEP_BETWEEN=0 ./scripts/run_all.sh
```

4) Schedule with cron (12:00 PM COL)

```bash
crontab -e
```

Add this line (adjust path):

```bash
0 12 * * * cd /opt/automatic && . venv/bin/activate && TZ=America/Bogota ./scripts/run_all.sh >> logs/cron_$(date +\%F).log 2>&1
```

Logs:

- Orchestrator run: `logs/run_all_YYYY-MM-DD_HH-mm-ss.log`
- Cron aggregate: `logs/cron_YYYY-MM-DD.log`

Notes:

- To export/upload XLSX, ensure the Service Account can write to the target Drive folder (Shared Drive) or set up domain-wide delegation.

## Notes

- `script.py` remains in place for now; new entrypoint is `app.py`.
- The scraper uses Playwright + Chromium; adjust headless with `HEADLESS`.
- Business rules and state normalization live in `services/tracker_service.py` and are driven by JSON mappings in project root.

## Async runner (recommended)

Use the modular async runner to control concurrency, batches and rate limiting:

```bash
python scripts/inter_process.py \
  --start-row 2 \
  --batch-size 500 \
  --max-concurrency 3 \
  --rps 0.8 \
  --retries 2 \
  --timeout-ms 45000
```

Parameters:

- `--start-row`: primera fila (1-based) a procesar.
- `--end-row`: última fila (opcional).
- `--limit`: máximo de filas a considerar (opcional).
- `--batch-size`: cantidad de guías por lote de navegador (default 500). Lotes grandes tardan en “arrancar”.
- `--max-concurrency`: páginas simultáneas (default 3). Impacta RAM/CPU.
- `--rps`: guías por segundo (espaciado de lanzamientos). Útil para evitar ráfagas.
- `--retries`: reintentos internos por guía si el estado llega vacío.
- `--timeout-ms`: timeout de navegación/esperas Playwright.
- `--headless true|false`: modo visible para depurar.
- `--only-empty`: procesar solo filas con `STATUS TRACKING` vacío.

Behavior:

- Se escribe en la hoja solo si el estado web no está vacío (no se sobreescribe con "").
- Se ignora el estado DROPi para decidir consultar: todo se resuelve por scraping.
- Las escrituras a Sheets van en bloques optimizados (columnas y tramos consecutivos) con troceo para evitar 4xx.

## Recommended settings (4GB RAM / 2 CPU)

- Seguro (producción estable):
  - `--batch-size 500` `--max-concurrency 2` `--rps 0.6` `--retries 2` `--timeout-ms 60000`
- Moderado (cobertura rápida):
  - `--batch-size 1000` `--max-concurrency 3` `--rps 0.8` `--retries 2` `--timeout-ms 45000`
- Visual (debug):
  - `--headless false` y lotes chicos `--limit 20 --batch-size 20`

Notas:

- `max-concurrency` consume RAM; con 4GB, 3 es tope razonable.
- `rps` controla ráfagas; 0.6–0.8 suele ser estable.

## Logging & observability

- Logs diarios: `logs/YYYY-MM-DD.log`.
- Trazas Playwright con prefijo `[PW]` muestran: creación de contextos, páginas, navegación, popup y extracción.
- Progreso por lote:
  - `Processing batch N with M items (rows X-Y)`
  - `Batch N progress: a/b (row idx, tn XXXXX)` cada 50 filas y al final del lote.
- Auditoría por tracking: `logs/statuses_YYYYMMDD.csv` (dropi/web raw y normalizado, alerta, vía).

## Examples

Producción moderada (1000 por lote):

```bash
python scripts/inter_process.py --start-row 4000 --batch-size 1000 --max-concurrency 3 --rps 0.8 --retries 2 --timeout-ms 45000
```

Solo filas con `STATUS TRACKING` vacío:

```bash
python scripts/inter_process.py --start-row 4000 --batch-size 1000 --max-concurrency 3 --rps 0.8 --retries 2 --timeout-ms 45000 --only-empty
```

## Compare statuses utility

Script to compare `STATUS DROPI` vs `STATUS TRACKING` and fill `COINCIDEN` and `ALERTA` using the same business rules as the updater.

- Normalization: both fields are normalized via `TrackerService.normalize_status()` before comparing.
- Coincidence: `COINCIDEN = TRUE` only if both normalized are non-empty and equal.
- Alert: computed via `TrackerService.compute_alert(dropi_norm, web_norm)`.
- Writes only when values change; sends batched updates to Sheets.

Usage:

```bash
python scripts/compare_statuses.py --start-row 2
python scripts/compare_statuses.py --start-row 500 --end-row 3000
python scripts/compare_statuses.py --start-row 2 --dry-run   # preview, no writes
```

## Autoría y origen

Este refactor fue desarrollado por mí a partir de un script previo ya existente; reutilicé su estructura como base para crear un producto más modular, mantenible y robusto.
