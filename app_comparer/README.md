# APP COMPARER - Comparador de Estados

Aplicación independiente para comparar estados entre Dropi e Interrapidísimo.

## **Responsabilidades**

- Leer STATUS DROPI y STATUS TRACKING desde Google Sheets
- Normalizar ambos estados a valores comparables
- Calcular columna COINCIDEN (TRUE/FALSE)
- Actualizar Google Sheets con resultados

## **Independencia Total**

Esta app es **completamente independiente** del sistema principal:

- ✅ Tiene su propio `requirements.txt`
- ✅ Tiene su propio `.env` (crea desde `.env.example`)
- ✅ Tiene su propio `credentials.json` (copia el archivo de Google)
- ✅ Tiene su propia carpeta `logs/`
- ✅ No depende de módulos del proyecto padre

## **Instalación**

```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar entorno
cp .env.example .env
# Editar .env con tu configuración

# 5. Copiar credenciales
# Copiar credentials.json de Google al directorio de esta app
```

## **Uso**

```bash
# Comparar todas las filas
python comparer_app.py

# Rango específico
python comparer_app.py --start-row 2 --end-row 100

# Modo dry-run (simular sin escribir)
python comparer_app.py --dry-run

# Batch size personalizado
python comparer_app.py --batch-size 1000
```

## **Estructura**

```
app_comparer/
├── comparer_app.py          # Entry point
├── comparer_config.py       # Configuración (.env)
├── comparer_logging.py      # Setup de logging
├── comparer_credentials.py  # Carga credentials.json
├── comparer_sheets.py       # Cliente Google Sheets
├── comparer_normalizer.py   # Normalización de estados
├── comparer_alerts.py       # Cálculo de alertas
├── dropi_map.json          # Mapeo estados Dropi
├── inter_map.json          # Mapeo estados Inter
├── requirements.txt         # Dependencias
├── .env.example            # Template de configuración
├── .gitignore              # Archivos ignorados
└── logs/                   # Logs de la app (auto-creado)
```

## **Configuración**

### `.env`

```env
SPREADSHEET_NAME=nombre_del_spreadsheet
BATCH_SIZE=5000
LOG_LEVEL=INFO
```

### `credentials.json`

Archivo de credenciales de Google Service Account con permisos:

- Google Sheets API
- Google Drive API

## **Reglas de Negocio**

### Normalización

Estados se normalizan a valores estándar:

- `EN_TRANSITO`
- `RECOLECTADO`
- `ENTREGADO`
- `DEVUELTO`
- `NOVEDAD`
- `CANCELADO`
- `PENDIENTE`

### Cálculo de COINCIDEN

```
COINCIDEN = TRUE si dropi_norm == web_norm
COINCIDEN = FALSE si no coinciden
```

## **Logs**

Los logs se guardan en `logs/comparer_YYYY-MM-DD.log` con:

- Timestamp
- Nivel (INFO, WARNING, ERROR)
- Función y línea
- Mensaje

## **Errores Comunes**

### `FileNotFoundError: credentials.json`

Solución: Copia el archivo de credenciales de Google a este directorio.

### `ValueError: SPREADSHEET_NAME es requerida`

Solución: Crea el archivo `.env` desde `.env.example` y configúralo.

### `gspread.exceptions.SpreadsheetNotFound`

Solución: Verifica que el nombre del spreadsheet en `.env` sea correcto y que la cuenta de servicio tenga acceso.

## **Testing**

```bash
# Dry run para probar sin escribir
python comparer_app.py --dry-run --start-row 2 --end-row 10

# Verificar logs
cat logs/comparer_$(date +%Y-%m-%d).log
```

## **Mantenimiento**

### Actualizar mapeos

Edita `dropi_map.json` o `inter_map.json` para agregar nuevos estados:

```json
{
  "NUEVO ESTADO RAW": "ESTADO_NORMALIZADO"
}
```

---

**Autor**: Sistema de Tracking Dropi-Inter  
**Versión**: 2.0.0  
**Fecha**: Octubre 2025
