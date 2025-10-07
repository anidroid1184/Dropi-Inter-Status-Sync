# APP MAKE DAILY REPORT - Generador de Reportes

Aplicación independiente para generar reportes diarios de discrepancias en formato Excel y subirlos a Google Drive.

## **Responsabilidades**

- Leer datos de Google Sheets
- Filtrar registros con COINCIDEN=FALSE (discrepancias)
- Generar archivo Excel formateado
- Subir archivo a Google Drive
- Logging de todas las operaciones

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
# Generar reporte (guarda en directorio actual)
python reporter_app.py

# Generar y subir a Drive
python reporter_app.py --upload

# Especificar directorio de salida
python reporter_app.py --output-dir ./reportes

# Modo dry-run (simular sin generar/subir)
python reporter_app.py --dry-run
```

## **Estructura**

```
app_make_dialy_report/
├── reporter_app.py          # Entry point
├── reporter_config.py       # Configuración (.env)
├── reporter_logging.py      # Setup de logging
├── reporter_credentials.py  # Carga credentials.json
├── reporter_sheets.py       # Cliente Google Sheets (lectura)
├── reporter_drive.py        # Cliente Google Drive (upload)
├── reporter_excel.py        # Generador de Excel
├── requirements.txt         # Dependencias
├── .env.example            # Template de configuración
├── .gitignore              # Archivos ignorados
└── logs/                   # Logs de la app (auto-creado)
```

## **Configuración**

### `.env`

```env
SPREADSHEET_NAME=nombre_del_spreadsheet
DRIVE_FOLDER_ID=id_de_carpeta_en_drive
LOG_LEVEL=INFO
```

### Obtener `DRIVE_FOLDER_ID`

1. Abre Google Drive
2. Navega a la carpeta donde quieres subir reportes
3. Copia el ID de la URL: `https://drive.google.com/drive/folders/[ID_AQUI]`

### `credentials.json`

Archivo de credenciales de Google Service Account con permisos:

- Google Sheets API (lectura)
- Google Drive API (escritura)

## **Flujo de Operación**

1. **Lectura**: Lee todos los registros de Google Sheets
2. **Filtrado**: Filtra solo registros con `COINCIDEN=FALSE` (discrepancias)
3. **Generación**: Crea archivo Excel con formato profesional
4. **Upload** (opcional): Sube archivo a carpeta de Drive especificada
5. **Logging**: Registra todas las operaciones en logs/

## **Formato del Excel**

- Headers con fondo azul y texto blanco
- Autoajuste de columnas
- Alineación centrada de headers
- Nombre: `discrepancias_YYYY-MM-DD.xlsx`

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

### `ValueError: DRIVE_FOLDER_ID es requerida`

Solución: Agrega el ID de carpeta de Drive en `.env`.

### `gspread.exceptions.SpreadsheetNotFound`

Solución: Verifica que el nombre del spreadsheet en `.env` sea correcto y que la cuenta de servicio tenga acceso.

### Error al subir a Drive

Solución: Verifica que la cuenta de servicio tenga permisos de escritura en la carpeta de Drive.

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
