# Configuration / Configuración

This document enumerates environment variables and configuration files used by the system.

Este documento enumera variables de entorno y archivos de configuración usados por el sistema.

## Environment variables (root) / Variables de entorno (raíz)
- `SPREADSHEET_NAME` (default: `seguimiento`)
- `HEADLESS` (default: `true`) – Playwright visible window when `false`.
- `TZ` (default: `America/Bogota`)
- `DAILY_REPORT_PREFIX` (default: `Informe_`)
- `DRIVE_FOLDER_ID` (optional): source folder for daily Excel.
- `DRIVE_FOLDER_INDIVIDUAL_FILE` (optional): per-file destination for individual report exports.

## Environment variables (Linux runner) / Variables (recreacion_linux)
- `HEADLESS` (default: `true`)
- `DEBUG_SCRAPER` (default: `false`)
- `BLOCK_RESOURCES` (default: `true`)
- `SLOW_MO` (default: `100` ms)
- `TIMEOUT_MS` (default: `120000` ms)
- `GOOGLE_APPLICATION_CREDENTIALS`: path to service account JSON.
- `INTER_MAP_PATH`: JSON mappings for Interrapidísimo keywords.
- `DROPI_MAP_PATH`: JSON mappings for DROPi keywords (optional).
- `PROXY_SERVER`, `PROXY_USERNAME`, `PROXY_PASSWORD` (optional)
- `SPREADSHEET_NAME`, `TZ`, `DAILY_REPORT_PREFIX`

## Files / Archivos
- `credentials.json`: Google Service Account JSON (not in git).
- `dropi_map.json`: Mapping `{ STATUS: [keywords...] }` (repo root by default).
- `interrapidisimo_traking_map.json`: Mapping `{ STATUS: [keywords...] }`.

## Notes / Notas
- Paths may be overridden by env vars in `TrackerService` via `DROPI_MAP_PATH` and `INTER_MAP_PATH`.
- `.env` at project root is recommended for local development.
