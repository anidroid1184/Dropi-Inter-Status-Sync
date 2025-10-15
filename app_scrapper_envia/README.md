# App Scraper Envía - Envía Status Scraper via 17track.net

Aplicación independiente para scraping de estados de tracking desde Envía vía 17track.net.

## 📋 Funcionalidad

- Scraping de estados desde portal web de 17track.net para Envía
- Procesa **hasta 40 guías simultáneamente** en un solo batch
- Extrae el estado **crudo** exactamente como aparece en la web (sin normalización)
- Actualiza solo la columna STATUS ENVIA con el texto crudo
- Soporte síncrono y asíncrono con procesamiento por batches
- Procesamiento por rangos y batches
- Logging completo de operaciones

**Nota Importante**: El scraper guarda el estado tal cual aparece en la web, removiendo solo el tiempo (ej: "En tránsito (2 Días)" -> "En tránsito"). La normalización y comparación se realiza en `app_comparer`.

## 🚀 Instalación

```bash
cd app_scrapper_envia
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuración

**IMPORTANTE: Esta app es completamente independiente**

1. Copiar `.env.example` a `.env` (en esta carpeta)
2. **Copiar tu `credentials.json` a esta carpeta `app_scrapper_envia/`**
3. Ajustar `SPREADSHEET_NAME` en `.env` para la hoja de Envía

```bash
# Estructura requerida:
app_scrapper_envia/
├── credentials.json     # ← TU ARCHIVO DE CREDENCIALES AQUÍ
├── .env                 # ← TU CONFIGURACIÓN AQUÍ
├── scraper_app.py
├── requirements.txt
└── ...
```

## 📝 Uso

```bash
# Scraping síncrono básico
python scraper_app.py

# Scraping asíncrono con concurrencia (RECOMENDADO para grandes volúmenes)
python scraper_app.py --async --concurrency 3

# Solo procesar filas sin estado
python scraper_app.py --only-empty

# Modo simulación (sin escribir cambios)
python scraper_app.py --dry-run

# Procesar rango específico
python scraper_app.py --start-row 2 --end-row 100

# Limitar cantidad de filas
python scraper_app.py --limit 50

# Batch size personalizado (por defecto: 40)
python scraper_app.py --async --batch-size 30
```

## 🌐 Cómo Funciona

Este scraper utiliza el sitio 17track.net que permite rastrear envíos de Envía:

1. **URL**: `https://www.17track.net/es/carriers/envía-envia`
2. **Método**: Ingresa hasta 40 guías en un textarea (una por línea)
3. **Resultados**: Los resultados se cargan en la misma página (no abre nueva pestaña)
4. **Extracción**:
   - ID de tracking desde: `<span title="014152617422" class="text-sm font-medium truncate">`
   - Status desde: `<div class="text-sm text-text-primary flex items-center gap-1">En tránsito (2 Días)</div>`
   - El status se limpia para remover el tiempo: "En tránsito (2 Días)" -> "En tránsito"

## 📊 Columna Actualizada

- **STATUS TRANSPORTADORA**: Columna donde se guarda el estado crudo de la web

## 📊 Estructura de la Hoja

La hoja de Google Sheets debe tener las siguientes columnas:

- **A - ID DROPI**: ID interno de Dropi
- **B - ID TRACKING**: Número de guía de Envía (se usa para scraping)
- **C - TRANSPORTADORA**: Nombre de la transportadora (debe contener "ENVIA")
- **D - STATUS DROPI**: Estado en Dropi
- **E - STATUS TRANSPORTADORA**: Estado de la transportadora (se actualiza por el scraper)
- **F - COINCIDEN**: Indicador de coincidencia de estados

## 🔄 Flujo de Trabajo

1. Lee registros de Google Sheets
2. Filtra según criterios (rango, vacíos, límite)
3. Procesa en batches de hasta 40 guías
4. Extrae estados del portal 17track.net
5. Actualiza columna STATUS ENVIA con estados crudos
6. Log completo de operaciones

## 🛠️ Arquitectura

- `scraper_app.py`: Lógica principal y CLI
- `scraper_web.py`: Scraper síncrono
- `scraper_web_async.py`: Scraper asíncrono con batches
- `scraper_sheets.py`: Cliente Google Sheets
- `scraper_config.py`: Configuración
- `scraper_logging.py`: Setup de logging
- `scraper_credentials.py`: Manejo de credenciales

## 🔍 Ejemplos de Estados Extraídos

```
"En tránsito"
"Entregado"
"En proceso"
"Devuelto"
```

## 📝 Notas

- El scraper NO normaliza estados - solo extrae el texto crudo
- La normalización se realiza en `app_comparer`
- Procesa hasta 40 guías por batch para máxima eficiencia
- Usa Playwright para navegación web robusta
- Maneja reintentos automáticos en caso de errores
  python scraper_app.py --async --concurrency 5

# Procesar rango específico

python scraper_app.py --start-row 100 --end-row 200

# Solo procesar filas sin estado

python scraper_app.py --only-empty

# Modo dry-run (simulación)

python scraper_app.py --dry-run --limit 10

```

## 📦 Dependencias

- playwright: Web scraping
- gspread: Google Sheets API
- oauth2client: Autenticación Google
- python-dotenv: Configuración

## 🔧 Parámetros

- `--start-row`: Fila inicial (default: 2)
- `--end-row`: Fila final (default: todas)
- `--limit`: Límite de filas
- `--async`: Usar scraper asíncrono
- `--concurrency`: Páginas concurrentes (default: 3)
- `--batch-size`: Tamaño de batch (default: 5000)
- `--only-empty`: Solo filas sin estado
- `--dry-run`: Simular sin escribir
```
