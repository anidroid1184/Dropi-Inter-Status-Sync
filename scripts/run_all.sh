#!/usr/bin/env bash
set -euo pipefail

# Run the full daily flow on Linux: scraper -> comparator -> report -> upload XLSX
# Logs are written with timestamp under logs/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

# Timezone (can be overridden via .env / exported TZ)
export TZ=${TZ:-America/Bogota}

# Activate venv
if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
else
  echo "[ERR] venv not found at $PROJECT_ROOT/venv. Create it and install requirements first." >&2
  exit 2
fi

STAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_LOG="logs/run_all_${STAMP}.log"
mkdir -p logs

PYTHON=${PYTHON:-python}

# Parameters (override via env if needed)
START_ROW=${START_ROW:-2}
END_ROW=${END_ROW:-}
LIMIT=${LIMIT:-}
BATCH_SIZE=${BATCH_SIZE:-1000}
MAX_CONCURRENCY=${MAX_CONCURRENCY:-3}
RPS=${RPS:-1.0}
RETRIES=${RETRIES:-2}
TIMEOUT_MS=${TIMEOUT_MS:-45000}
SLEEP_BETWEEN=${SLEEP_BETWEEN:-0}
ONLY_EMPTY=${ONLY_EMPTY:-}
HEADLESS=${HEADLESS:-true}
DATE_ARG=${DATE_ARG:-}

exec_step() {
  echo "[RUN] $*" | tee -a "$RUN_LOG"
  "$@" 2>&1 | tee -a "$RUN_LOG"
}

# 1) Scraper
SCRAPER_CMD=(
  "$PYTHON" scripts/inter_process.py
  --start-row "$START_ROW"
  --batch-size "$BATCH_SIZE"
  --max-concurrency "$MAX_CONCURRENCY"
  --rps "$RPS"
  --retries "$RETRIES"
  --timeout-ms "$TIMEOUT_MS"
  --sleep-between-batches "$SLEEP_BETWEEN"
  --headless "$HEADLESS"
)
[[ -n "${END_ROW}" ]] && SCRAPER_CMD+=(--end-row "$END_ROW")
[[ -n "${LIMIT}" ]] && SCRAPER_CMD+=(--limit "$LIMIT")
[[ -n "${ONLY_EMPTY}" ]] && SCRAPER_CMD+=(--only-empty)
exec_step "${SCRAPER_CMD[@]}"

# 2) Comparador
COMPARE_CMD=("$PYTHON" scripts/compare_statuses.py --start-row "$START_ROW")
[[ -n "${END_ROW}" ]] && COMPARE_CMD+=(--end-row "$END_ROW")
exec_step "${COMPARE_CMD[@]}"

# 3) Informe diario (ambos IDs, hora COL ya soportada)
REPORT_CMD=("$PYTHON" scripts/make_daily_report.py --start-row "$START_ROW")
[[ -n "${END_ROW}" ]] && REPORT_CMD+=(--end-row "$END_ROW")
[[ -n "${LIMIT}" ]] && REPORT_CMD+=(--limit "$LIMIT")
[[ -n "${DATE_ARG}" ]] && REPORT_CMD+=(--date "$DATE_ARG")
exec_step "${REPORT_CMD[@]}"

# 4) Upload XLSX (requiere carpeta de destino o delegación)
UPLOAD_CMD=("$PYTHON" scripts/upload_daily_report_xlsx.py --replace)
[[ -n "${DATE_ARG}" ]] && UPLOAD_CMD+=(--date "$DATE_ARG")
exec_step "${UPLOAD_CMD[@]}"

echo "[OK] run_all finished. Log: $RUN_LOG" | tee -a "$RUN_LOG"
