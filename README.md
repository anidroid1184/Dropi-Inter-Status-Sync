# Interrapidísimo Tracker — Bilingual README / README Bilingüe

This project updates Interrapidísimo tracking statuses into Google Sheets using a Playwright-based scraper and business logic for normalization and alerting.

Este proyecto actualiza estados de Interrapidísimo en Google Sheets usando un scraper basado en Playwright y reglas de negocio para normalización y alertas.

## Documentation / Documentación

- See `docs/Overview.md`, `docs/Architecture.md`, `docs/Modules-and-APIs.md`, `docs/Configuration.md`, `docs/Operations-Runbook.md`, `docs/Troubleshooting.md`, `docs/Data-Mappings.md`, `docs/Testing.md`, and `docs/ADRs/*`.
- Linux-focused runner docs: `recreacion_linux/README.md`.

- Ver `docs/Overview.md`, `docs/Architecture.md`, `docs/Modules-and-APIs.md`, `docs/Configuration.md`, `docs/Operations-Runbook.md`, `docs/Troubleshooting.md`, `docs/Data-Mappings.md`, `docs/Testing.md` y `docs/ADRs/*`.
- Documentación del runner para Linux: `recreacion_linux/README.md`.

## Structure / Estructura

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
│  ├─ inter_scraper.py        # Legacy scraper (sync)
│  └─ inter_scraper_async.py  # Async scraper (preferred)
├─ scripts/
│  ├─ inter_process.py        # Async modular runner
│  └─ compare_statuses.py     # Compare DROPi vs web and write flags
├─ recreacion_linux/          # Linux-optimized headless runner
└─ docs/                      # Technical documentation
└─ tests/
   └─ test_tracker_service.py # Unit tests for core business logic
```

## Requirements / Requisitos

- Python 3.10+
- `credentials.json` (Service Account) in the project root (not committed)

Install deps / Instalar dependencias:

```bash
pip install -r requirements.txt
# Install Playwright browser binaries (one-time)
python -m playwright install chromium
```

Ubuntu 25.04 note / Nota Ubuntu 25.04:

- Avoid running `playwright install-deps` on Ubuntu 25.04; dependency validation may fail or try to fetch incompatible packages.
- If Playwright refuses to run due to host requirement validation, set the environment variable to bypass validation:

```bash
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
```

Diagnostic (headful via virtual display) / Diagnóstico (con pantalla virtual):

```bash
# Run headed inside a virtual Xorg session to observe UI timing / iframe mounting
sudo apt-get update && sudo apt-get install -y xvfb
HEADLESS=false DEBUG_SCRAPER=true BLOCK_RESOURCES=false \
  xvfb-run -a -s "-screen 0 1280x800x24" \
  python -m recreacion_linux.main scrape-to-csv --count 3 --rps 0.5 --timeout-ms 120000 --slow-mo 100
```

## Environment / Entorno

Create a `.env` file (no secrets):

```ini
DRIVE_FOLDER_ID=...        # Google Drive folder ID with daily Excel
SPREADSHEET_NAME=seguimiento
HEADLESS=false             # false to see the browser while debugging; set true in production
TZ=America/Bogota
DAILY_REPORT_PREFIX=Informe_
```

## Quickstart (Windows, venv) / Inicio rápido (Windows, venv)

Step-by-step with PowerShell / Paso a paso con PowerShell:

```powershell
# 1) Clone / Clonar
git clone <REPO_URL> automatic
cd automatic

# 2) Create and activate venv / Crear y activar entorno
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Install dependencies / Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4) Install Playwright browser / Instalar navegador de Playwright (Chromium)
python -m playwright install chromium

# 5) Prepare environment / Preparar entorno
# - Place credentials.json in project root / Poner credentials.json en la raíz
# - Copy .env.example to .env and edit values / Copiar .env.example a .env y editar
Copy-Item .env.example .env -Force
# Edit .env to set HEADLESS=true/false, etc. / Editar .env para HEADLESS=true/false, etc.

# 6) Run (async, recommended) / Ejecutar (asíncrono, recomendado)
python app.py --async --start-row 2 --limit 50 --max-concurrency 3

# (Optional) Run sync / (Opcional) Ejecutar modo síncrono
python app.py --start-row 2 --limit 50
```

Notes / Notas:

- Set `HEADLESS=false` in `.env` to see the browser while debugging locally; set `HEADLESS=true` for CI/servers.
- Ensure `credentials.json` corresponds to a Google Service Account with access to the target sheet and drive folder.

## Docker (optional) / Docker (opcional)

```bash
# Build (if needed)
docker build -t inter-tracker .
# Compose example (ensure volumes/env mapping for .env, credentials.json and logs/)
docker compose run --rm app bash -lc "python scripts/inter_process.py --start-row 2 --max-concurrency 2 --rps 0.8"
```

## Cron (1–2am COL)

Example (Linux cron):

```bash
0 2 * * * /bin/bash -lc 'cd /path/automatic && source venv/bin/activate && python app.py --start-row 2 >> logs/$(date +\%F).log 2>&1'
```

## Notes

- `script.py` remains in place for now; new entrypoint is `app.py`.
- The scraper uses Playwright + Chromium; adjust headless with `HEADLESS`.
- Business rules and state normalization live in `services/tracker_service.py` and are driven by JSON mappings in project root.

## Async runner (recommended) / Runner asíncrono (recomendado)

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

App entrypoint (async flag) / Entrada principal (bandera asíncrona):

```bash
python app.py --async --start-row 2 --limit 50 --max-concurrency 3
```

Parameters / Parámetros:

- `--start-row`: primera fila (1-based) a procesar.
- `--end-row`: última fila (opcional).
- `--limit`: máximo de filas a considerar (opcional).
- `--batch-size`: cantidad de guías por lote de navegador (default 500). Lotes grandes tardan en “arrancar”.
- `--max-concurrency`: páginas simultáneas (default 3). Impacta RAM/CPU.
- `--rps`: guías por segundo (espaciado de lanzamientos). Útil para evitar ráfagas.
- `--retries`: reintentos internos por guía si el estado llega vacío.
- `--timeout-ms`: timeout de navegación/esperas Playwright.
- `--batch-size`: tamaño de lote para el scraping asíncrono (filas por ciclo de navegador). Default 5000.
- `--post-compare`: después del scraping, ejecuta la comparación (COINCIDEN/ALERTA) antes del Daily Report.
- `--compare-batch-size`: tamaño de lote para la comparación. Default 5000.

Behavior (post-compare) / Comportamiento (post-compare):

- Cuando se usa `--post-compare`, la comparación se ejecuta sobre toda la hoja (desde la fila 2 hasta el final), independientemente del rango de scraping. Luego se genera/apende el Daily Report si hubo diferencias.
- `--headless true|false`: modo visible para depurar.
- `--only-empty`: procesar solo filas con `STATUS TRACKING` vacío.

Behavior / Comportamiento:

- Se escribe en la hoja solo si el estado web no está vacío (no se sobreescribe con "").
- Se ignora el estado DROPi para decidir consultar: todo se resuelve por scraping.
- Las escrituras a Sheets van en bloques optimizados (columnas y tramos consecutivos) con troceo para evitar 4xx.

## Recommended settings (4GB RAM / 2 CPU) / Configuración recomendada (4GB RAM / 2 CPU)

- Seguro (producción estable):
  - `--batch-size 500` `--max-concurrency 2` `--rps 0.6` `--retries 2` `--timeout-ms 60000`
- Moderado (cobertura rápida):
  - `--batch-size 1000` `--max-concurrency 3` `--rps 0.8` `--retries 2` `--timeout-ms 45000`
- Visual (debug):
  - `--headless false` y lotes chicos `--limit 20 --batch-size 20`

Notas:

- `max-concurrency` consume RAM; con 4GB, 3 es tope razonable.
- `rps` controla ráfagas; 0.6–0.8 suele ser estable.

## Logging & observability / Observabilidad

- Logs diarios: `logs/YYYY-MM-DD.log`.
- Trazas Playwright con prefijo `[PW]` muestran: creación de contextos, páginas, navegación, popup y extracción.
- Progreso por lote:
  - `Processing batch N with M items (rows X-Y)`
  - `Batch N progress: a/b (row idx, tn XXXXX)` cada 50 filas y al final del lote.
- Auditoría por tracking: `logs/statuses_YYYYMMDD.csv` (dropi/web raw y normalizado, alerta, vía).

## Examples / Ejemplos

Producción moderada (1000 por lote):

```bash
python scripts/inter_process.py --start-row 4000 --batch-size 1000 --max-concurrency 3 --rps 0.8 --retries 2 --timeout-ms 45000
```

Solo filas con `STATUS TRACKING` vacío:

```bash
python scripts/inter_process.py --start-row 4000 --batch-size 1000 --max-concurrency 3 --rps 0.8 --retries 2 --timeout-ms 45000 --only-empty
```

End-to-end (async app) / Fin-a-fin (app asíncrona):

Prueba acotada (sin Drive, rango pequeño, post-compare y daily report):

```bash
python app.py --async --skip-drive \
  --start-row 2 --end-row 200 \
  --max-concurrency 3 --batch-size 1000 \
  --post-compare --compare-batch-size 1000
```

Proceso grande (toda la hoja por lotes, post-compare sobre toda la hoja):

```bash
python app.py --async --skip-drive \
  --start-row 2 \
  --max-concurrency 3 --batch-size 5000 \
  --post-compare --compare-batch-size 5000
```

## Compare statuses utility / Utilitario de comparación

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
