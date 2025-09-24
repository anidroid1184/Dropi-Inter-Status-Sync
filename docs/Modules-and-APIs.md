# Modules and APIs / Módulos y APIs

This document describes the main public modules, their responsibilities, and key methods with inputs/outputs.

Este documento describe los módulos públicos principales, sus responsabilidades y métodos clave con inputs/outputs.

## services/sheets_client.py
- Class: `SheetsClient(credentials, spreadsheet_name)`
  - `sheet() -> Worksheet`: returns main worksheet.
  - `read_main_records() -> List[Dict]`: legacy reader (stops at first blank row).
  - `read_main_records_resilient() -> List[Dict]`: uses `get_all_values()` to avoid early stop.
  - `read_headers() -> List[str]`
  - `ensure_headers(headers: List[str]) -> None`: adds missing headers at row 1.
  - `append_new_rows(rows: List[List[Any]]) -> int`: appends rows and expands sheet if required.
  - `update_range(a1: str, values: List[List[Any]]) -> None`: with simple retry/backoff.
  - `values_batch_update(data: List[Dict], value_input_option='RAW') -> Any`: batched updates for disjoint ranges.
  - `create_or_append_daily_report(rows, prefix='Informe_') -> str`: ensure or append in a daily-named sheet.

## services/tracker_service.py
- Class: `TrackerService`
  - Purpose: normalization, alerting, decisions; drives from JSON mappings + overrides + heuristics.
  - `normalize_status(s: str) -> str`
  - `explain_normalization(s: str) -> dict`: {matched, via, keyword, status, raw}
  - `compute_alert(dropi: str, tracking: str) -> str` -> "TRUE" | "FALSE"
  - `can_query(dropi: str) -> bool`
  - `terminal(dropi: str, tracking: str) -> bool`
  - `prepare_new_rows(source_data: List[Dict], existing_guias: set) -> List[List[str]]`

## web/inter_scraper_async.py
- Class: `AsyncInterScraper`
  - `start()` / `close()` lifecycle management of Playwright.
  - `get_status(tracking_number: str) -> str`: robust extraction (popup/iframe/page) with fallbacks and debug dumps.
  - `get_status_many(tracking_numbers: Iterable[str], rps: float|None) -> List[Tuple[str,str]]`: bounded concurrency, retries, spacing by RPS.
  - Flags: `headless`, `max_concurrency`, `retries`, `timeout_ms`, `block_resources`, `debug`, proxy options.

## scripts/inter_process.py
- CLI async runner for mass updates with batching.
- Args: `--start-row`, `--end-row`, `--limit`, `--max-concurrency`, `--rps`, `--retries`, `--timeout-ms`, `--headless`, `--batch-size`, `--sleep-between-batches`, `--only-empty`.
- Delegates to `app.update_statuses_async(...)`.

## app.py
- `update_statuses(...)` (sync): sequential scraper (legacy) + batch writes.
- `update_statuses_async(...)`: async pipeline recommended for production.
- `_flush_batch(...)`: groups updates by column index then by consecutive row blocks; sends chunked batch updates.

## Configuration / Configuración
- Root: `config.settings`
  - `SPREADSHEET_NAME`, `HEADLESS`, `TZ`, `DAILY_REPORT_PREFIX`, `DRIVE_FOLDER_ID`.
- Linux recreation package: `recreacion_linux.config.settings`
  - Includes `DEBUG_SCRAPER`, `BLOCK_RESOURCES`, `SLOW_MO`, `TIMEOUT_MS`, mapping paths via env.

## Conventions / Convenciones
- All write operations to Sheets must be batched via `values_batch_update`.
- Never overwrite with empty status; only write if non-empty.
- Use `explain_normalization` to capture raw statuses not covered by mappings.
