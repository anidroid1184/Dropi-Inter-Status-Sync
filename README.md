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

## Cron (1–2am COL)

Example (Linux cron):

```bash
0 2 * * * /bin/bash -lc 'cd /path/automatic && source venv/bin/activate && python app.py --start-row 2 >> logs/$(date +\%F).log 2>&1'
```

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
