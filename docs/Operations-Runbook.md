# Operations Runbook / Manual de Operación

This runbook describes day-to-day operations, from running locally to monitoring and recovery.

Este manual describe operaciones del día a día: ejecución local, monitoreo y recuperación.

## Local execution (Windows) / Ejecución local (Windows)
- Create and activate venv
```
python -m venv .venv
.venv\Scripts\activate
```
- Install dependencies
```
pip install -r requirements.txt
python -m playwright install chromium
```
- Place `credentials.json` at project root.
- Create `.env` at project root (see Configuration.md and .env.example).
- Run async runner (recommended):
```
python scripts/inter_process.py --start-row 2 --limit 100 --max-concurrency 2 --rps 0.6 --retries 2 --timeout-ms 60000 --only-empty
```

## Local execution (Linux) / Ejecución local (Linux)
- See `recreacion_linux/README.md` for a headless runner with file-only logs.

## Docker (optional) / Docker (opcional)
- Build (if needed): `docker build -t inter-tracker .`
- Compose (example):
```
docker compose run --rm app bash -lc "python scripts/inter_process.py --start-row 2 --max-concurrency 2 --rps 0.6"
```
Ensure volumes and env files map `credentials.json`, `.env`, and `logs/` appropriately.

## Monitoring / Monitoreo
- Daily log: `logs/YYYY-MM-DD.log`.
- Per-tracking audit CSV: `logs/statuses_YYYYMMDD.csv`.
- Playwright debug artifacts (HTML/PNG/NDJSON) appear with prefixes in `logs/` when enabled or on failures.

## Recovery and retries / Recuperación y reintentos
- Blanks: the async runner performs a second pass per batch.
- Timeouts: increase `--timeout-ms`, reduce `--max-concurrency`, set `--rps` to 0.6–0.8.
- Anti-bot issues: set `HEADLESS=false` to observe, and `BLOCK_RESOURCES=false` during diagnosis.
- Sheets 429/quota: batch updates are chunked and retried with backoff; re-run later if still throttled.

## Batch sizing guidance / Guía de tamaño de lotes
- 4GB RAM: `--max-concurrency 2`, `--rps 0.6–0.8`, `--batch-size 500–1000`.
- Visual debugging: `--headless false`, smaller limits: `--limit 20 --batch-size 20`.

## Daily report / Informe diario
- Differences between DROPi and web status are appended to `Informe_YYYY-MM-DD` (configurable via `DAILY_REPORT_PREFIX`).

## Change management / Gestión de cambios
- Use `docs/ADRs/*` for architectural decisions.
- Update `Data-Mappings.md` when extending mappings; keep a PR checklist.
