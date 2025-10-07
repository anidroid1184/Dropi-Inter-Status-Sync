# Sistema de Tracking Dropi-Inter

**Versión 3.0.0 - Arquitectura de Microservicios**

Sistema automatizado para sincronización de estados de paquetes entre Dropi e Interrapidísimo, con **3 aplicaciones independientes y escalables**.

This project provides automated package status synchronization between Dropi and Interrapidísimo systems, featuring **3 independent and scalable microservices**.

## 🚀 Nueva Arquitectura: 3 Apps Independientes

Este proyecto ha evolucionado de un monolito a **3 aplicaciones completamente independientes**:

### 1. **APP SCRAPER** - Scraping de Web
- 📂 `app_scrapper/`
- 🎯 Scraping síncrono/asíncrono de Interrapidísimo
- 📝 Actualiza columna STATUS TRACKING en Google Sheets
- ⚡ Playwright para navegación automatizada

### 2. **APP COMPARER** - Comparador de Estados
- 📂 `app_comparer/`
- 🎯 Compara STATUS DROPI vs STATUS TRACKING
- 📝 Calcula columnas COINCIDEN y ALERTA
- 🧠 Normalización inteligente de estados

### 3. **APP MAKE DAILY REPORT** - Generador de Reportes
- 📂 `app_make_dialy_report/`
- 🎯 Genera reportes Excel con alertas
- 📝 Sube reportes a Google Drive
- 📊 Formato profesional automático

## ✨ Ventajas de la Nueva Arquitectura

- **Independencia Total**: Cada app con su propio `venv`, `.env`, `credentials.json`
- **Escalabilidad**: Cada app puede desplegarse en diferentes servidores
- **Mantenibilidad**: Cambios en una app no afectan a las demás
- **Testing Aislado**: Pruebas unitarias por app sin dependencias cruzadas
- **Deploy Independiente**: Actualiza solo la app que necesitas
- **Microservicios Ready**: Arquitectura lista para Docker/Kubernetes

## 📚 Documentación

### Apps Independientes
- 📘 **`app_scrapper/README.md`** - Documentación completa del Scraper
- 📗 **`app_comparer/README.md`** - Documentación completa del Comparador
- 📙 **`app_make_dialy_report/README.md`** - Documentación completa del Reporter

### Sistema General (Legacy)
- Ver `docs/Overview.md`, `docs/Architecture.md`, `docs/Modules-and-APIs.md`, etc.

---

## 🚀 Inicio Rápido

### Opción 1: Apps Independientes (Recomendado)

Cada app se instala y ejecuta por separado:

```bash
# 1. APP SCRAPER
cd app_scrapper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env y copiar credentials.json
python scraper_app.py --async

# 2. APP COMPARER
cd ../app_comparer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env y copiar credentials.json
python comparer_app.py

# 3. APP REPORTER
cd ../app_make_dialy_report
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env y copiar credentials.json
python reporter_app.py --upload
```

### Opción 2: Sistema Legacy (Monolito)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

---

## 📁 Estructura del Proyecto

```text
automatic/
├─ app_scrapper/                   # 🆕 APP 1: Scraper independiente
│  ├─ scraper_app.py               #    Entry point
│  ├─ scraper_config.py            #    Configuración local
│  ├─ scraper_web.py               #    Scraper sincrónico
│  ├─ scraper_web_async.py         #    Scraper asíncrono
│  ├─ requirements.txt             #    Dependencias
│  └─ README.md                    #    Documentación
│
├─ app_comparer/                   # 🆕 APP 2: Comparador independiente
│  ├─ comparer_app.py              #    Entry point
│  ├─ comparer_normalizer.py       #    Normalización de estados
│  ├─ comparer_alerts.py           #    Cálculo de alertas
│  ├─ dropi_map.json               #    Mapeo estados
│  ├─ requirements.txt             #    Dependencias
│  └─ README.md                    #    Documentación
│
├─ app_make_dialy_report/          # 🆕 APP 3: Reporter independiente
│  ├─ reporter_app.py              #    Entry point
│  ├─ reporter_excel.py            #    Generador Excel
│  ├─ reporter_drive.py            #    Upload a Drive
│  ├─ requirements.txt             #    Dependencias
│  └─ README.md                    #    Documentación
│
├─ core/                           # Sistema Legacy
├─ services/                       # Servicios Legacy
├─ utils/                          # Utilidades Legacy
├─ web/                            # Scrapers Legacy
├─ scripts/                        # Scripts Legacy
├─ docs/                           # Documentación
├─ deprecated/                     # Archivos obsoletos
└─ README.md                       # Este archivo
```

### 🆕 Nuevos Componentes

- **Módulo `core/`**: Lógica central de la aplicación modularizada
- **`status_normalizer.py`**: Normalizador especializado con soporte JSON
- **`alert_calculator.py`**: Calculador inteligente de alertas y reglas
- **`credentials_manager.py`**: Gestión segura y centralizada de credenciales
- **`batch_operations.py`**: Operaciones batch optimizadas para Google Sheets
- **`constants.py`**: Constantes del sistema centralizadas y tipadas

### 🔄 Componentes Refactorizados

- **`tracker_service.py`**: Ahora actúa como fachada coordinadora
- **`app.py`**: Función main simplificada con manejo de errores robusto
- **Módulo `utils/`**: Expandido con nuevas utilidades especializadas

## Features / Características

- Asynchronous scraping with Playwright + Chromium (concurrency, retries, RPS).
- Status normalization and alerting with configurable JSON mappings.
- Batch writes to Google Sheets to reduce API calls.
- Post-compare step to compute `COINCIDEN` and `ALERTA` over the whole sheet.
- Daily report generation that replaces the sheet every run.
- Detailed logging and per-tracking audit CSV.

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

<!-- Diagnostic virtual display section removed (Linux recreation not used in this repo) -->

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

Example (Linux cron) / Ejemplo (cron en Linux):

```bash
0 2 * * * /bin/bash -lc 'cd /path/automatic && source venv/bin/activate && python app.py --start-row 2 >> logs/$(date +\%F).log 2>&1'
```

## Notes / Notas

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
  python app.py --async --skip-drive --start-row 2 --max-concurrency 3 --batch-size 1000 --post-compare --compare-batch-size 1000
```

Report-only (regenerate daily report) / Solo informe (regenerar informe diario):

- Recalcula la comparación en toda la hoja y reescribe el informe, sin scrapear filas (útil para refrescar el informe del día).

```bash
python app.py --async --skip-drive \
  --start-row 2 --limit 0 \
  --max-concurrency 1 --batch-size 1 \
  --post-compare --compare-batch-size 20000
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
