# Testing / Pruebas

## Unit tests / Pruebas unitarias
- Focus on `services/tracker_service.py` normalization and alert rules.
- Add tests under `tests/` (e.g., `tests/test_tracker_service.py`).

Example (pytest):
```python
import pytest
from services.tracker_service import TrackerService

def test_normalize_entregado():
    assert TrackerService.normalize_status("Entregado") == "ENTREGADO"

def test_override_pendiente_admitir():
    assert TrackerService.normalize_status("Envío pendiente por admitir") == "PENDIENTE"

def test_alert_entregado_mismatch():
    assert TrackerService.compute_alert("ENTREGADO", "EN_TRANSITO") == "TRUE"
```

## Integration tests / Pruebas de integración
- Mock Google Sheets using `gspread` stubs or a sandbox sheet.
- Validate `_flush_batch` writes only changed cells and splits ranges correctly.

## Scraper standalone / Scraper aislado
- Provide a list of tracking IDs in `input/sample_tracking.txt` and run a standalone script to produce `out/sample_statuses.csv` without Google Sheets interaction. Useful to isolate Playwright behavior.

## Manual validation / Validación manual
- Run `scripts/inter_process.py` on a small range with `--only-empty` and inspect:
  - `logs/YYYY-MM-DD.log` for Playwright traces.
  - `logs/statuses_YYYYMMDD.csv` for per-tracking audit.
  - `logs/status_catalog.json` for newly observed raw statuses.
