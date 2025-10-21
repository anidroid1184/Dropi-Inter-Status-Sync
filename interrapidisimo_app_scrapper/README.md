# App Scraper - Interrapidísimo Status Scraper

Aplicación independiente para scraping de estados de tracking desde Interrapidísimo.

## 📋 Funcionalidad

- Scraping de estados desde portal web de Interrapidísimo
- Extrae el estado **crudo** exactamente como aparece en la web (sin normalización)
- Actualiza solo la columna STATUS INTERRAPIDISIMO con el texto crudo
- Soporte síncrono y asíncrono
- Procesamiento por rangos y batches
- Logging completo de operaciones

**Nota Importante**: El scraper guarda el estado tal cual aparece en la web (ej: "Tu envío Fue devuelto", "Tú envío fue entregado"). La normalización y comparación se realiza en `app_comparer`.

## 🚀 Instalación

```bash
cd app_scrapper
python -m venv venv
source venv/bin/activate  # Windows: 
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuración

**IMPORTANTE: Esta app es completamente independiente**

1. Copiar `.env.example` a `.env` (en esta carpeta)
2. **Copiar tu `credentials.json` a esta carpeta `app_scrapper/`**
3. Ajustar `SPREADSHEET_NAME` en `.env`

```bash
# Estructura requerida:
app_scrapper/
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

# Scraping asíncrono con concurrencia
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
