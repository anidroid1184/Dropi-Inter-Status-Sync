# 🧪 Tests del Scraper de Envía

## 📁 Estructura de Tests

Esta carpeta contiene todos los scripts de prueba y utilidades para el scraper de Envía.

```
tests/
├── __init__.py              # Marca el directorio como paquete Python
├── README.md               # Este archivo
├── test_textarea_fill.py   # Prueba visual del llenado de textarea
├── test_visual.py          # Prueba visual completa del scraper
└── list_sheets.py          # Utilidad para listar hojas de Google Sheets
```

## 🧪 Scripts de Prueba

### 1. `test_textarea_fill.py`

**Propósito:** Verificar que los códigos de tracking se ingresen correctamente en el textarea.

**Uso:**

```bash
cd envia_app_scrapper
python tests/test_textarea_fill.py
```

**Qué verás:**

- ✅ Navegador Chrome se abre (modo visible)
- ✅ Navega a 17track.net
- ✅ Llena el textarea con 5 códigos de prueba
- ✅ Mantiene el navegador abierto 10 segundos para inspección

**Códigos de prueba usados:**

```
014152617422
014152617423
014152617424
014152617425
014152617426
```

---

### 2. `test_visual.py`

**Propósito:** Depurar el proceso completo del scraper con navegador visible.

**Uso:**

```bash
cd envia_app_scrapper
python tests/test_visual.py
```

**Qué verás:**

- ✅ Navegador Chrome se abre (modo visible)
- ✅ Proceso completo de scraping paso a paso
- ✅ Llenado de textarea
- ✅ Click en botón "Rastrear"
- ✅ Extracción de resultados
- ✅ Logs detallados en consola

**Códigos de prueba usados:**

```
14152626978
14152627016
14152627038
```

⚠️ **Nota:** Puedes modificar estos códigos editando el archivo para usar tus propios IDs de tracking.

---

### 3. `list_sheets.py`

**Propósito:** Listar todas las hojas de Google Sheets a las que tienes acceso.

**Uso:**

```bash
cd envia_app_scrapper
python tests/list_sheets.py
```

**Qué verás:**

```
============================================================
HOJAS DE GOOGLE SHEETS DISPONIBLES
============================================================

1. Nombre: Tracking Dropi-Inter
   ID: 1abc123def456...
   URL: https://docs.google.com/spreadsheets/d/...

2. Nombre: Otra Hoja
   ID: 2xyz789ghi012...
   URL: https://docs.google.com/spreadsheets/d/...
```

**Utilidad:**

- Verificar el nombre exacto de tu hoja
- Copiar el ID de la hoja
- Confirmar que las credenciales funcionan

---

## 🚀 Cómo Ejecutar los Tests

### Desde la raíz del proyecto:

```bash
# Test de textarea
python tests/test_textarea_fill.py

# Test visual completo
python tests/test_visual.py

# Listar hojas de Google Sheets
python tests/list_sheets.py
```

### Desde la carpeta tests:

```bash
cd tests

# Test de textarea
python test_textarea_fill.py

# Test visual completo
python test_visual.py

# Listar hojas de Google Sheets
python list_sheets.py
```

## 📝 Requisitos

Todos los tests usan los módulos del directorio padre:

- `scraper_web_async.py` - Scraper asíncrono
- `scraper_credentials.py` - Carga de credenciales
- `scraper_logging.py` - Configuración de logs
- `scraper_config.py` - Configuración general

**No necesitas instalar nada adicional**, los tests usan las mismas dependencias que el scraper principal.

## 🔧 Configuración

Los tests buscan automáticamente los archivos de configuración en el directorio padre:

- `credentials.json` - Credenciales de Google
- `.env` - Variables de entorno

**Asegúrate de tener estos archivos configurados** antes de ejecutar los tests.

## 🐛 Debugging

### Si los tests fallan por imports:

```python
ModuleNotFoundError: No module named 'scraper_web_async'
```

**Solución:** Los tests ya incluyen código para agregar el directorio padre al path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

Si aún falla, ejecuta desde la raíz del proyecto:

```bash
cd envia_app_scrapper
python tests/test_visual.py
```

### Si el navegador no se abre:

1. Verifica que Playwright esté instalado:

   ```bash
   playwright install chromium
   ```

2. Si el problema persiste:
   ```bash
   pip install playwright --upgrade
   playwright install chromium
   ```

### Si las credenciales fallan:

1. Verifica que `credentials.json` existe en `envia_app_scrapper/`
2. Ejecuta `list_sheets.py` para confirmar acceso:
   ```bash
   python tests/list_sheets.py
   ```

## 📊 Ejemplo de Output

### test_textarea_fill.py

```
2025-10-21 10:30:15 - INFO - === PRUEBA VISUAL DE TEXTAREA ===
2025-10-21 10:30:15 - INFO - Códigos de prueba: ['014152617422', '014152617423', ...]
2025-10-21 10:30:16 - INFO - [PW] Starting async_playwright...
2025-10-21 10:30:16 - INFO - [PW] Launching Chromium. headless=False
2025-10-21 10:30:18 - INFO - Scraper iniciado. Procesando batch...
2025-10-21 10:30:25 - INFO - [PW] Textarea found!
2025-10-21 10:30:25 - INFO - [PW] Filled 5 tracking numbers via JavaScript
2025-10-21 10:30:25 - INFO - [PW] Textarea content verified: 62 characters
2025-10-21 10:30:26 - INFO - [PW] Rastrear button found!
2025-10-21 10:30:26 - INFO - [PW] Clicked Rastrear button successfully
2025-10-21 10:30:35 - INFO - === RESULTADOS ===
2025-10-21 10:30:35 - INFO -   014152617422: En tránsito
2025-10-21 10:30:35 - INFO -   014152617423: Entregado
2025-10-21 10:30:35 - INFO - === PRUEBA COMPLETADA ===
```

## 💡 Tips

1. **Usa test_visual.py para debugging inicial** - Te muestra todo el proceso
2. **Usa test_textarea_fill.py para verificar ingreso de códigos** - Más rápido y enfocado
3. **Usa list_sheets.py cuando cambies de hoja** - Verifica nombres e IDs
4. **Modifica los códigos de prueba** - Usa tus propios IDs de tracking para probar con datos reales
5. **Revisa los logs** - Los tests generan logs detallados en consola

## 🎯 Casos de Uso

### Caso 1: "Los códigos no se ingresan"

```bash
python tests/test_textarea_fill.py
```

Observa si el textarea se llena correctamente.

### Caso 2: "El botón no se hace click"

```bash
python tests/test_visual.py
```

Observa si encuentra y hace click en el botón "Rastrear".

### Caso 3: "No puedo conectar a Google Sheets"

```bash
python tests/list_sheets.py
```

Verifica que las credenciales funcionen.

### Caso 4: "Quiero probar con mis propios códigos"

Edita `test_visual.py` y cambia:

```python
test_tracking = [
    "TU_CODIGO_1",
    "TU_CODIGO_2",
    "TU_CODIGO_3"
]
```

## ✅ Checklist de Tests

Antes de usar el scraper en producción, verifica:

- [ ] `test_textarea_fill.py` pasa sin errores
- [ ] Los códigos se ven en el textarea
- [ ] El botón "Rastrear" se hace click
- [ ] `test_visual.py` extrae status correctamente
- [ ] `list_sheets.py` muestra tus hojas
- [ ] Las credenciales de Google funcionan
- [ ] El scraper completo funciona con `--limit 5`

## 🚨 Troubleshooting

| Problema                | Solución                            |
| ----------------------- | ----------------------------------- |
| Import errors           | Ejecuta desde `envia_app_scrapper/` |
| Playwright no instalado | `playwright install chromium`       |
| Credenciales inválidas  | Verifica `credentials.json`         |
| Navegador no abre       | Verifica Playwright instalado       |
| Timeout en botón        | Aumenta timeout en código           |
| No extrae resultados    | Aumenta sleep después de click      |

## 📚 Documentación Relacionada

- [README.md](../README.md) - Documentación principal del scraper
- [MEJORAS_CLICK_BOTON.md](../MEJORAS_CLICK_BOTON.md) - Detalles del sistema de click
- [.env.example](../.env.example) - Ejemplo de configuración

---

¿Dudas? Revisa los comentarios dentro de cada script de test. 💡
