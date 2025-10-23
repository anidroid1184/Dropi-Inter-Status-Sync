"""
Scraper Simple para Coordinadora.

Usa requests + BeautifulSoup para obtener el estado de una guía.
Mucho más rápido y simple que Playwright.

Uso:
    from scraper_coordinadora import obtener_estado
    estado = obtener_estado("36394323151")
    print(estado)  # "Entregado"
"""

import requests
from bs4 import BeautifulSoup
import logging

# URL base de Coordinadora
BASE_URL = "https://coordinadora.com/rastreo/rastreo-de-guia/detalle-de-rastreo-de-guia/?guia="

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def obtener_estado(guia: str, timeout: int = 30) -> str:
    """
    Obtiene el estado de una guía de Coordinadora.

    Args:
        guia: Número de guía a consultar
        timeout: Timeout en segundos para la petición

    Returns:
        Estado de la guía (ej: "Entregado", "En terminal destino")
        String vacío si hay error
    """
    url = f"{BASE_URL}{guia}"

    try:
        logger.info(f"Consultando guía {guia}...")

        # Hacer petición HTTP
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Parsear HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Estrategia 1: Buscar "Estado del paquete" y tomar el siguiente span
        estado_paquete = soup.find('span', class_='strong-text title',
                                   string=lambda t: t and 'Estado del paquete' in t)

        if estado_paquete:
            # Buscar el siguiente span con clase "strong-text title"
            parent = estado_paquete.find_parent()
            if parent:
                spans = parent.find_all('span', class_='strong-text title')
                if len(spans) >= 2:
                    estado = spans[1].get_text(strip=True)
                    logger.info(f"✓ Estado encontrado: {estado}")
                    return estado

        # Estrategia 2: Buscar en div.detail con "Estado de la guía:"
        detail_div = soup.find('div', class_='detail')
        if detail_div:
            estado_guia_span = detail_div.find('span', class_='light-text',
                                               string=lambda t: t and 'Estado de la guía:' in t)
            if estado_guia_span:
                # El siguiente span con clase "strong-text title" tiene el estado
                siguiente = estado_guia_span.find_next_sibling(
                    'span', class_='strong-text title')
                if siguiente:
                    estado = siguiente.get_text(strip=True)
                    logger.info(f"✓ Estado encontrado: {estado}")
                    return estado

        # Estrategia 3: Buscar cualquier span.strong-text.title después de "Estado de la guía:"
        estado_label = soup.find(
            'span', string=lambda t: t and 'Estado de la guía:' in t)
        if estado_label:
            siguiente = estado_label.find_next(
                'span', class_='strong-text title')
            if siguiente:
                estado = siguiente.get_text(strip=True)
                logger.info(f"✓ Estado encontrado: {estado}")
                return estado

        logger.warning(f"No se encontró estado para guía {guia}")
        return ""

    except requests.exceptions.Timeout:
        logger.error(f"Timeout al consultar guía {guia}")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al consultar guía {guia}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Error inesperado al procesar guía {guia}: {e}")
        return ""


if __name__ == "__main__":
    # Prueba con la guía del ejemplo
    guia_prueba = "36394323151"
    print(f"\n🔍 Probando con guía: {guia_prueba}")
    print("="*50)

    estado = obtener_estado(guia_prueba)

    if estado:
        print(f"✅ Estado: {estado}")
    else:
        print("❌ No se pudo obtener el estado")

    print("="*50)
