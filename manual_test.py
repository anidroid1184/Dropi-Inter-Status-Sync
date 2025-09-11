from __future__ import annotations
import asyncio
import logging
import os
import random
import time
from typing import List, Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import unicodedata

# ==============================
# Configuración (rellenar por ti)
# ==============================

# URL del portal de tracking
TRACKING_URL: str = "https://interrapidisimo.com/sigue-tu-envio/"

# ¿Se abre una nueva pestaña/ventana tras buscar?
EXPECT_NEW_PAGE: bool = True

# Selector del input de búsqueda (puede ser CSS o XPath). Ejemplos:
# CSS por id: "#inputGuide"
# XPath: "//input[@id='inputGuide']"
SEARCH_INPUT_SELECTOR: str = "inputGuideMovil"  # TODO: rellena

# Selector del elemento que contiene el estado final. Ejemplos:
# XPath: "//h2[contains(text(),'envío')]/following-sibling::p"
# CSS: "div.estado, p.status"
STATUS_SELECTOR: str = "number-tracking"        # TODO: rellena

# Selector del CONTENEDOR PADRE para match por mapa (clase "-number-tracking").
# Puedes cambiarlo a un XPath si prefieres.
STATUS_PARENT_SELECTOR: str = ".-number-tracking"

# Ruta del mapa de frases -> estado canónico (Interrapidísimo)
INTER_MAP_PATH: str = "interrapidisimo_traking_map.json"

# Activar intento de resolución por mapa usando el contenedor padre
USE_MAP_MATCH: bool = True

# Lista de 10 guías a consultar
TRACKING_NUMBERS: List[str] = [
    # TODO: rellena con 10 guías
    # "1234567890",
    "240035207134",
    "240035207146",
    "240035207152",
    "240035207158",
    "240035207167",
    "240035207175",
    "240035207183",
    "240035207191",
    "240035207202",
]

# Headless apagado para ver la interacción
HEADLESS: bool = False

# Timeout (ms) para esperas explícitas
TIMEOUT_MS: int = 15000

# Pausa aleatoria entre 1 y 3 segundos entre consultas
PAUSE_RANGE_SECONDS = (1.0, 3.0)

# ==============================
# Fin de configuración
# ==============================


def setup_logging() -> None:
    """
    Está función se encarga de genrar los logs
    """
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "manual_test.log")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Evita duplicar handlers si se re-ejecuta
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

    logging.info("Log inicializado en: %s", log_path)


async def wait_random_pause():
    """
    Está funcion crea las pausas entre requests
    """
    low, high = PAUSE_RANGE_SECONDS
    await asyncio.sleep(random.uniform(low, high))


def _normalize_text(s: str) -> str:
    """Convierte a minúsculas y elimina acentos para comparaciones robustas."""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def _load_inter_map(path: str) -> dict:
    if not os.path.exists(path):
        logging.warning("Mapa no encontrado: %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # normalizamos frases de búsqueda para evitar problemas de acentos/mayúsculas
            norm_map = {}
            for canon, phrases in data.items():
                norm_map[canon] = [_normalize_text(p) for p in phrases]
            return norm_map
    except Exception as e:
        logging.exception("Error cargando mapa %s: %s", path, e)
        return {}


INTER_MAP = _load_inter_map(INTER_MAP_PATH)


def match_status_using_map(container_text: str) -> Optional[str]:
    """Intenta mapear el texto del contenedor a un estado canónico usando INTER_MAP.

    Se hace por coincidencia de subcadenas (substring) normalizadas.
    """
    if not INTER_MAP:
        return None
    norm_text = _normalize_text(container_text)
    for canon, phrases in INTER_MAP.items():
        for ph in phrases:
            if ph and ph in norm_text:
                return canon
    return None


def get_locator(page, selector: str):
    """Construye un locator a partir de un selector dado.

    - Si empieza con "//": XPath.
    - Si empieza con "#" o ".": CSS directo.
    - En otro caso, se asume que es un ID y se convierte a CSS con prefijo '#'.
    """
    sel = selector.strip()
    if not sel:
        return None
    if sel.startswith("//"):
        return page.locator(f"xpath={sel}")
    if sel.startswith("#") or sel.startswith("."):
        return page.locator(sel)
    # tratar como id simple
    return page.locator(f"#{sel}")


async def get_status_for_tracking(page, tracking: str) -> Optional[str]:
    """
    Ingresa una guía en el buscador, navega a la vista de detalle (si aplica) y
    devuelve el texto del estado encontrado.
    """
    # Ir a la URL principal para cada consulta (aislar estado UI)
    await page.goto(TRACKING_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

    # Buscar input
    input_locator = get_locator(page, SEARCH_INPUT_SELECTOR)
    await input_locator.wait_for(timeout=TIMEOUT_MS)

    # Ingresar guía y Enter
    await input_locator.fill("")
    await input_locator.type(tracking, delay=20)
    await input_locator.press("Enter")

    # Manejar apertura de nueva página si aplica
    target_page = page
    if EXPECT_NEW_PAGE:
        try:
            # Espera a popup OR cambio de contexto
            with page.context.expect_page(timeout=TIMEOUT_MS) as new_page_info:
                # En algunos sitios el Enter dispara navegación; si no ocurre,
                # un clic extra o esperar ayuda. Ajustable si tu flujo es distinto.
                pass
            new_page = await new_page_info.value
            target_page = new_page
            await target_page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
        except PlaywrightTimeoutError:
            # Si no se abrió, intenta continuar en la misma página
            target_page = page

    # 1) Intento por MAPA desde el CONTENEDOR PADRE (si está configurado)
    if USE_MAP_MATCH and STATUS_PARENT_SELECTOR:
        parent_locator = get_locator(target_page, STATUS_PARENT_SELECTOR)
        if parent_locator is not None:
            try:
                await parent_locator.wait_for(timeout=TIMEOUT_MS)
                parent_text = (await parent_locator.first.inner_text()).strip()
                match = match_status_using_map(parent_text)
                if match:
                    return match
            except PlaywrightTimeoutError:
                # seguir con respaldo por STATUS_SELECTOR
                pass

    # 2) Respaldo: buscar STATUS_SELECTOR directo y devolver su texto
    if STATUS_SELECTOR:
        status_locator = get_locator(target_page, STATUS_SELECTOR)
        if status_locator is not None:
            try:
                await status_locator.wait_for(timeout=TIMEOUT_MS)
                text = (await status_locator.first.inner_text()).strip()
                return text
            except PlaywrightTimeoutError:
                return None
    return None


async def run() -> int:
    setup_logging()

    # Validaciones básicas
    if not SEARCH_INPUT_SELECTOR:
        logging.error("Debes completar SEARCH_INPUT_SELECTOR antes de ejecutar.")
        return 2
    if not (STATUS_SELECTOR or (USE_MAP_MATCH and STATUS_PARENT_SELECTOR)):
        logging.error("Debes configurar STATUS_SELECTOR o activar USE_MAP_MATCH con STATUS_PARENT_SELECTOR.")
        return 2
    if not TRACKING_NUMBERS:
        logging.error("Debes completar TRACKING_NUMBERS con tus 10 guías.")
        return 2

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, args=["--start-maximized"])
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        successes, failures = 0, 0

        for idx, guia in enumerate(TRACKING_NUMBERS, start=1):
            try:
                logging.info("(%d/%d) Consultando guía: %s", idx, len(TRACKING_NUMBERS), guia)
                status = await get_status_for_tracking(page, guia)
                if status:
                    logging.info("Guía %s | Estado: %s", guia, status)
                    successes += 1
                else:
                    logging.warning("Guía %s | Estado no encontrado", guia)
                    failures += 1
            except Exception as e:
                logging.exception("Error consultando %s: %s", guia, e)
                failures += 1

            await wait_random_pause()

        await context.close()
        await browser.close()

        logging.info("Finalizado. Éxitos: %d | Fallos: %d", successes, failures)
        return 0 if failures == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run())
    except KeyboardInterrupt:
        logging.warning("Interrumpido por el usuario.")
        exit_code = 130
    raise SystemExit(exit_code)