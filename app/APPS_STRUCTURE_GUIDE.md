# GUÍA DE ESTRUCTURA - 3 APPS INDEPENDIENTES

## ✅ YA CREADO

### APP SCRAPER (`app_scrapper/`)
- ✅ `scraper_app.py` - Aplicación principal
- ✅ `requirements.txt` - Dependencias
- ✅ `.env.example` - Configuración ejemplo
- ✅ `scraper_config.py` - Configuración
- ✅ `scraper_logging.py` - Logging
- ✅ `scraper_credentials.py` - Credenciales
- ✅ `scraper_sheets.py` - Cliente Sheets
- ✅ `scraper_web.py` - Scraper síncrono (copiado)
- ✅ `scraper_web_async.py` - Scraper asíncrono (copiado)
- ✅ `README.md` - Documentación

### APP COMPARER (`app_comparer/`)
- ✅ `comparer_app.py` - Aplicación principal
- ✅ `requirements.txt` - Dependencias
- ✅ `.env.example` - Configuración ejemplo

## 📝 PENDIENTE POR CREAR

### APP COMPARER - Archivos restantes
```bash
cd app_comparer

# Copiar archivos necesarios del proyecto principal
cp ../services/status_normalizer.py ./comparer_normalizer.py
cp ../services/alert_calculator.py ./comparer_alerts.py
cp ../app_scrapper/scraper_config.py ./comparer_config.py
cp ../app_scrapper/scraper_logging.py ./comparer_logging.py
cp ../app_scrapper/scraper_credentials.py ./comparer_credentials.py
cp ../app_scrapper/scraper_sheets.py ./comparer_sheets.py
```

### APP REPORT (`app_make_dialy_report/`)
Crear todos los archivos:
- `report_app.py` - Aplicación principal
- `requirements.txt` - Dependencias (pandas, gspread, oauth2client, python-dotenv, openpyxl)
- `.env.example` - Configuración
- `report_config.py` - Configuración
- `report_logging.py` - Logging
- `report_credentials.py` - Credenciales
- `report_sheets.py` - Cliente Sheets con lógica de reporte
- `README.md` - Documentación

## 🚀 COMANDOS RÁPIDOS

### Para completar APP COMPARER:
```bash
cd /mnt/c/Users/juans/OneDrive/Documents/automatic/automatic/app_comparer

# Crear archivos de configuración básicos (copias de scraper)
cp ../app_scrapper/scraper_config.py ./comparer_config.py
cp ../app_scrapper/scraper_logging.py ./comparer_logging.py  
cp ../app_scrapper/scraper_credentials.py ./comparer_credentials.py
cp ../app_scrapper/scraper_sheets.py ./comparer_sheets.py

# Copiar lógica de normalización y alertas
cp ../services/status_normalizer.py ./comparer_normalizer.py
cp ../services/alert_calculator.py ./comparer_alerts.py

# Crear README
cat > README.md << 'EOF'
# App Comparer - Comparador de Estados

Aplicación independiente para comparar estados Dropi vs Interrapidísimo.

## Instalación
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso
```bash
python comparer_app.py
python comparer_app.py --start-row 100 --end-row 500
python comparer_app.py --dry-run
```
EOF
```

### Para crear APP REPORT completa:
```bash
cd /mnt/c/Users/juans/OneDrive/Documents/automatic/automatic/app_make_dialy_report

# Copiar base desde app_scrapper
cp ../app_scrapper/scraper_config.py ./report_config.py
cp ../app_scrapper/scraper_logging.py ./report_logging.py
cp ../app_scrapper/scraper_credentials.py ./report_credentials.py

# Copiar cliente sheets y adaptar
cp ../app_scrapper/scraper_sheets.py ./report_sheets.py
```

## 📋 PRÓXIMOS PASOS

1. ✅ Ejecutar comandos de copia para APP COMPARER
2. ⬜ Crear APP REPORT completa
3. ⬜ Ajustar imports en archivos copiados (renombrar clases si es necesario)
4. ⬜ Crear .gitignore para cada app (venv/, .env, __pycache__, logs/)
5. ⬜ Probar cada app de forma independiente
6. ⬜ Documentar en README principal

## 🎯 RESULTADO FINAL

3 aplicaciones completamente independientes:
- `app_scrapper/` - Scraping de estados
- `app_comparer/` - Comparación y alertas
- `app_make_dialy_report/` - Generación de reportes

Cada una con:
- ✅ Su propio venv
- ✅ Sus propias dependencias (requirements.txt)
- ✅ Su propia configuración (.env)
- ✅ Su propia documentación (README.md)
- ✅ Ejecución independiente
