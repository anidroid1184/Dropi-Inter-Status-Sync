# APP COMPARER - Comparador de Estados

Aplicación independiente para comparar estados entre Dropi e Interrapidísimo.

## **Responsabilidades**

- Leer STATUS DROPI y STATUS INTERRAPIDISIMO (texto crudo) desde Google Sheets
- Normalizar STATUS INTERRAPIDISIMO usando `inter_map.json`
- Comparar estados normalizados
- Calcular columna COINCIDEN (TRUE/FALSE)
- Actualizar Google Sheets con resultados

**Flujo de datos**:

1. Lee STATUS DROPI: "ENTREGADO" (ya normalizado)
2. Lee STATUS INTERRAPIDISIMO: "Tu envío fue entregado" (texto crudo de la web)
3. Busca en inter_map.json: {"ENTREGADO": ["tu envío fue entregado", ...]}
4. Encuentra coincidencia → inter_normalized = "ENTREGADO"
5. Compara: "ENTREGADO" == "ENTREGADO"
6. Marca COINCIDEN = TRUE

**Ejemplo con discrepancia**:

1. STATUS DROPI: "EN_TRANSITO"
2. STATUS INTERRAPIDISIMO: "Tu envío Fue devuelto"
3. Normaliza usando mapa → "REENVIO"
4. Compara: "EN_TRANSITO" != "REENVIO"
5. Marca COINCIDEN = FALSE

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
├── comparer_normalizer.py   # Normalización usando mapa
├── inter_map.json          # Mapeo palabras clave → variantes texto crudo
├── requirements.txt         # Dependencias
├── .env.example            # Template de configuración
├── .gitignore              # Archivos ignorados
├── test_normalizer.py      # Script de prueba del normalizador
└── logs/                   # Logs de la app (auto-creado)
```

**Nota**: Ya no se usa `dropi_map.json` ni `comparer_alerts.py`.

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

### inter_map.json

Archivo JSON con mapeo de palabras clave a variantes de texto crudo:

```json
{
  "ENTREGADO": [
    "entregado",
    "tu envio fue entregado",
    "tu envío fue entregado",
    "tú envío fue entregado",
    "recibido",
    ...
  ],
  "REENVIO": [
    "tu envio fue devuelto",
    "tu envío fue devuelto",
    "devuelto al remitente",
    "retorno a origen",
    ...
  ],
  ...
}
```

### Normalización

El normalizador busca coincidencias parciales:

- Texto crudo: "Tu envío fue entregado"
- Busca en todas las palabras clave y sus variantes
- Encuentra: "tu envío fue entregado" en la lista de "ENTREGADO"
- Retorna: "ENTREGADO"

### Cálculo de COINCIDEN

**Entrada**:

- `STATUS DROPI`: "ENTREGADO" (ya normalizado)
- `STATUS INTERRAPIDISIMO`: "Tú envío fue entregado" (texto crudo)

**Proceso**:

1. Normaliza STATUS INTERRAPIDISIMO → "ENTREGADO"
2. Normaliza STATUS DROPI (solo limpieza) → "ENTREGADO"
3. Compara: "ENTREGADO" == "ENTREGADO"

**Salida**:

```
COINCIDEN = TRUE
```

**Ejemplo con discrepancia**:

- STATUS DROPI: "EN_TRANSITO"
- STATUS INTERRAPIDISIMO: "Tu envío Fue devuelto"
- Normalizado: "REENVIO"
- Comparación: "EN_TRANSITO" != "REENVIO"
- Resultado: COINCIDEN = FALSE

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
