# APP MAKE DAILY REPORT - Generador de Reportes

Aplicación independiente para generar reportes diarios de discrepancias creando una nueva hoja en el mismo spreadsheet de Google Sheets.

## **Responsabilidades**

- Leer datos de Google Sheets
- Filtrar registros con COINCIDEN=FALSE (discrepancias)
- Crear nueva hoja en el spreadsheet con las discrepancias
- Formatear la nueva hoja (headers con color, congelar fila)
- Logging de todas las operaciones

**IMPORTANTE**: Esta app NO genera archivos Excel ni sube a Drive.  
Crea una nueva hoja (sheet) dentro del mismo archivo de Google Sheets.

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
# Generar reporte (crea nueva hoja en el spreadsheet)
python reporter_app.py

# Especificar nombre de hoja personalizado
python reporter_app.py --sheet-name "reporte_2025-01-07"

# Modo dry-run (simular sin crear hoja)
python reporter_app.py --dry-run
```

## **Estructura**

```
app_make_dialy_report/
├── reporter_app.py          # Entry point
├── reporter_config.py       # Configuración (.env)
├── reporter_logging.py      # Setup de logging
├── reporter_credentials.py  # Carga credentials.json
├── reporter_sheets.py       # Cliente Google Sheets (lectura y escritura)
├── requirements.txt         # Dependencias
├── .env.example            # Template de configuración
├── .gitignore              # Archivos ignorados
├── test_filter.py          # Script de prueba del filtrado
└── logs/                   # Logs de la app (auto-creado)
```

**Nota**: `reporter_drive.py` y `reporter_excel.py` ya no se usan.

## **Configuración**

### `.env`

```env
SPREADSHEET_NAME=nombre_del_spreadsheet
LOG_LEVEL=INFO
```

**Nota**: Ya no se necesita `DRIVE_FOLDER_ID`.

### `credentials.json`

Archivo de credenciales de Google Service Account con permisos:

- Google Sheets API (lectura y escritura)

## **Flujo de Operación**

1. **Lectura**: Lee todos los registros de la hoja principal de Google Sheets
2. **Filtrado**: Filtra solo registros con `COINCIDEN=FALSE` (discrepancias)
3. **Creación**: Crea una nueva hoja en el mismo spreadsheet
4. **Escritura**: Escribe las discrepancias en la nueva hoja
5. **Formato**: Aplica formato a los headers (color azul, texto blanco, negrita)
6. **Logging**: Registra todas las operaciones en logs/

## **Formato de la Hoja Creada**

### Estructura del Reporte

La nueva hoja incluye **TODAS las columnas** del spreadsheet, pero solo para registros con `COINCIDEN=FALSE`:

**Columnas principales**:

- `GUIA`: Número de guía
- `STATUS DROPI`: Estado en Dropi (normalizado)
- `STATUS INTERRAPIDISIMO`: Texto crudo de la web (ej: "Tu envío Fue devuelto")
- `COINCIDEN`: Siempre "FALSE" en el reporte (por eso es discrepancia)
- ... todas las demás columnas del spreadsheet

### Formato Visual

- Headers con fondo azul (#4472C4) y texto blanco en negrita
- Primera fila congelada (frozen)
- Headers centrados
- Nombre de hoja: `discrepancias_YYYY-MM-DD` (o personalizado)

### Ejemplo de Discrepancia

```
GUIA: 12345
STATUS DROPI: EN_TRANSITO
STATUS INTERRAPIDISIMO: Tu envío Fue devuelto
COINCIDEN: FALSE
```

Esto significa que Dropi dice "EN_TRANSITO" pero la web de Interrapidísimo muestra "Tu envío Fue devuelto" (que se normaliza a "REENVIO"), por lo que hay una discrepancia.

### Ubicación

La hoja se crea en el **mismo archivo de Google Sheets** donde están los datos principales.  
Puedes verla en las pestañas inferiores del spreadsheet.

## **Logs**

Los logs se guardan en `logs/reporter_YYYY-MM-DD.log` con:

- Timestamp
- Nivel (INFO, WARNING, ERROR)
- Función y línea
- Mensaje detallado

## **Errores Comunes**

### `FileNotFoundError: credentials.json`

Solución: Copia el archivo de credenciales de Google a este directorio.

### `ValueError: SPREADSHEET_NAME es requerida`

Solución: Crea el archivo `.env` desde `.env.example` y configúralo.

### `gspread.exceptions.SpreadsheetNotFound`

Solución: Verifica que el nombre del spreadsheet en `.env` sea correcto y que la cuenta de servicio tenga acceso.

### `gspread.exceptions.APIError: Permission denied`

Solución: Verifica que la cuenta de servicio tenga permisos de **edición** en el spreadsheet (no solo lectura).

## **Testing**

```bash
# Dry run para probar sin generar/subir
python reporter_app.py --dry-run

# Generar sin subir
python reporter_app.py --output-dir ./test

# Verificar logs
cat logs/reporter_$(date +%Y-%m-%d).log
```

## **Integración con Scheduler**

### Windows Task Scheduler

```powershell
# Tarea diaria a las 8:00 AM
schtasks /create /tn "DropisReporteDiario" /tr "C:\ruta\a\venv\Scripts\python.exe C:\ruta\a\reporter_app.py --upload" /sc daily /st 08:00
```

### Linux Cron

```bash
# Tarea diaria a las 8:00 AM
0 8 * * * cd /ruta/a/app && /ruta/a/venv/bin/python reporter_app.py --upload
```

## **Mantenimiento**

### Cambiar formato de Excel

Edita `reporter_excel.py` en el método `_apply_formatting()`.

### Agregar columnas específicas

Modifica el filtrado en `reporter_app.py` en la función `generate_report()`:

```python
# Ejemplo: filtrar solo columnas específicas
df = pd.DataFrame(data)[['GUIA', 'STATUS DROPI', 'STATUS TRACKING', 'COINCIDEN']]
```

---

**Autor**: Sistema de Tracking Dropi-Inter  
**Versión**: 2.0.0  
**Fecha**: Enero 2025
