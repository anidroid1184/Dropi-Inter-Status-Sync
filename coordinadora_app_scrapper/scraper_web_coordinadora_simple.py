"""
Scraper ligero para Coordinadora usando requests + BeautifulSoup.

Este módulo es independiente y no reemplaza ni mueve archivos existentes.
Está pensado para consultas rápidas a la URL pública:
https://coordinadora.com/rastreo/rastreo-de-guia/detalle-de-rastreo-de-guia/?guia=ID

Extrae el estado usando las mismas estrategias de selectores que el
scraper basado en Playwright (`scraper_web_coordinadora.py`).
"""
from __future__ import annotations
import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup


class CoordinadoraSimple:
    """Consulta la página pública de Coordinadora y extrae el estado.

    Uso mínimo:
        from scraper_config import settings
        s = CoordinadoraSimple(base_url=settings.base_url)
        estado = s.get_status('36394323151')
    """

    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout

    def get_status(self, tracking_number: str) -> str:
        url = f"{self.base_url}{tracking_number}"
        logging.info("Consultando Coordinadora (simple) %s", url)

        try:
            resp = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; CoordinadoraScraper/1.0)"
                    )
                },
            )
            resp.raise_for_status()
        except Exception as e:
            logging.error("Error HTTP al consultar %s: %s", url, e)
            return ""

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Estrategia 1: Buscar span con texto "Estado del paquete"
            estado = self._strategy_span_after_label(soup)
            if estado:
                return estado

            # Estrategia 2: Buscar div.detail que contenga "Estado de la guía:"
            estado = self._strategy_div_detail(soup)
            if estado:
                return estado

            # Estrategia 3: Buscar label "Estado de la guía:" y tomar
            # siguiente span
            estado = self._strategy_label_next_span(soup)
            if estado:
                return estado

            logging.warning("No se encontró el estado en la página %s", url)
            return ""

        except Exception as e:
            logging.error("Error al parsear HTML de %s: %s", url, e)
            return ""

    def _strategy_span_after_label(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            # Buscar span con clase 'strong-text title' que contenga
            # 'Estado del paquete'
            spans = soup.select('span.strong-text.title')
            for i, span in enumerate(spans):
                if (
                    span.get_text(strip=True)
                    .lower()
                    .startswith('estado del paquete')
                ):
                    # intentar el siguiente span con la clase
                    if i + 1 < len(spans):
                        return spans[i + 1].get_text(strip=True)
            return None
        except Exception:
            return None

    def _strategy_div_detail(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            # Buscar div.detail que contenga 'Estado de la guía:'
            for div in soup.select('div.detail'):
                if (
                    div.find('span', class_='light-text')
                    and 'Estado de la guía' in div.get_text()
                ):
                    span = div.select_one('span.strong-text.title')
                    if span:
                        return span.get_text(strip=True)
            return None
        except Exception:
            return None

    def _strategy_label_next_span(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            labels = soup.select('span.light-text')
            for label in labels:
                if 'Estado de la guía' in label.get_text():
                    parent = label.parent
                    if not parent:
                        continue
                    span = parent.select_one('span.strong-text.title')
                    if span:
                        return span.get_text(strip=True)
            return None
        except Exception:
            return None


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    app_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(app_dir, '.env')
    load_dotenv(env_path)
    from scraper_config import settings

    s = CoordinadoraSimple(base_url=settings.base_url)
    ejemplo = '36394323151'
    print('Consultando ejemplo:', ejemplo)
    print('Estado:', s.get_status(ejemplo))
