"""
Scraper Web para Coordinadora.

Este módulo maneja el scraping directo de estados de Coordinadora
usando acceso directo a URLs sin interacción compleja con la página.

Responsabilidades:
- Scraping directo usando URL con ID de guía
- Extracción de estado desde elemento HTML específico
- Sin necesidad de navegación compleja o interacción con formularios
- Manejo de timeouts y errores

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import logging
from contextlib import suppress
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


class CoordinadoraScraper:
    """
    Scraper para obtener estados de tracking desde Coordinadora.
    
    Utiliza acceso directo a URL con el ID de la guía:
    https://coordinadora.com/rastreo/rastreo-de-guia/detalle-de-rastreo-de-guia/?guia=ID
    
    El estado se extrae desde:
    <span class="strong-text title">Estado del paquete</span>
    
    Dentro del elemento padre:
    <div class="detail">
        <span class="light-text">Estado de la guía:</span>
        <span class="strong-text title">ESTADO AQUÍ</span>
        ...
    </div>
    """

    def __init__(self, headless: bool = True, base_url: str = ""):
        """
        Inicializa el scraper de Coordinadora.
        
        Args:
            headless: Si True, ejecuta el browser sin interfaz gráfica
            base_url: URL base para construir las URLs de tracking
        """
        self._pw = sync_playwright().start()
        self._headless = headless
        self._base_url = base_url
        
        logging.info(
            "Iniciando Playwright Chromium para Coordinadora. headless=%s",
            headless
        )

        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        
        slow_mo = 250 if not headless else 0
        if not headless:
            launch_args.append("--start-maximized")

        self.browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=launch_args,
        )

    def get_status(self, tracking_number: str) -> str:
        """
        Obtiene el estado de una guía de Coordinadora.
        
        Args:
            tracking_number: Número de guía a consultar
            
        Returns:
            Estado extraído de la web, o string vacío si hay error
        """
        context = None
        page = None

        try:
            # Crear nuevo contexto
            if self._headless:
                context = self.browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
            else:
                context = self.browser.new_context(viewport=None)

            page = context.new_page()

            # Construir URL con el ID de tracking
            url = f"{self._base_url}{tracking_number}"
            
            logging.info(
                "Consultando estado para guía: %s",
                tracking_number
            )
            logging.debug("URL: %s", url)

            # Navegar a la URL
            page.goto(url, timeout=45000, wait_until="domcontentloaded")

            # Esperar a que cargue la página
            page.wait_for_timeout(3000)

            # Intentar cerrar banners de cookies si aparecen
            with suppress(Exception):
                cookie_btn = page.locator(
                    'button:has-text("Aceptar"), '
                    'button:has-text("Acepto"), '
                    'button[aria-label*="cookie"]'
                ).first
                if cookie_btn.is_visible(timeout=2000):
                    cookie_btn.click(timeout=2000)
                    logging.debug("Banner de cookies cerrado")

            # Buscar el estado del paquete
            # Primero buscamos el span con "Estado del paquete"
            estado = self._extract_status(page)

            if estado:
                logging.info(
                    "Estado extraído para %s: %s",
                    tracking_number,
                    estado
                )
                return estado
            else:
                logging.warning(
                    "No se pudo extraer estado para guía: %s",
                    tracking_number
                )
                return ""

        except PlaywrightTimeoutError as e:
            logging.error(
                "Timeout al consultar guía %s: %s",
                tracking_number,
                e
            )
            return ""
        except Exception as e:
            logging.error(
                "Error al procesar guía %s: %s",
                tracking_number,
                e
            )
            return ""

        finally:
            with suppress(Exception):
                if page:
                    page.close()
            with suppress(Exception):
                if context:
                    context.close()

    def _extract_status(self, page) -> str:
        """
        Extrae el estado del paquete desde la página.
        
        Busca el elemento:
        <span class="strong-text title">Entregado</span>
        
        Que está después de "Estado del paquete"
        
        Args:
            page: Página de Playwright
            
        Returns:
            Estado extraído o string vacío
        """
        try:
            # Estrategia 1: Buscar directamente el span con clase
            # "strong-text title" que está cerca de "Estado del paquete"
            
            # Primero intentamos encontrar el contenedor con
            # "Estado del paquete"
            estado_label = page.locator(
                'span.strong-text.title:has-text("Estado del paquete")'
            )
            
            if estado_label.count() > 0:
                logging.debug("Encontrado label 'Estado del paquete'")
                
                # El estado está en el siguiente span con clase
                # "strong-text title"
                # Buscamos en el elemento padre
                parent = estado_label.locator('xpath=ancestor::div[1]')
                
                # Dentro del padre, buscamos los spans con la clase
                estado_spans = parent.locator('span.strong-text.title')
                
                # El segundo span debería ser el estado
                if estado_spans.count() >= 2:
                    estado = estado_spans.nth(1).inner_text(timeout=5000)
                    return estado.strip()
            
            # Estrategia 2: Buscar en el div.detail que contiene
            # "Estado de la guía:"
            logging.debug("Intentando estrategia 2: div.detail")
            
            detail_div = page.locator(
                'div.detail:has(span.light-text:has-text("Estado de la guía:"))'
            )
            
            if detail_div.count() > 0:
                logging.debug("Encontrado div.detail con 'Estado de la guía'")
                
                # Dentro de este div, buscar el span con clase
                # "strong-text title"
                estado_span = detail_div.locator(
                    'span.strong-text.title'
                ).first
                
                if estado_span.count() > 0:
                    estado = estado_span.inner_text(timeout=5000)
                    return estado.strip()
            
            # Estrategia 3: Buscar cualquier span después del texto
            # "Estado de la guía:"
            logging.debug("Intentando estrategia 3: búsqueda general")
            
            estado_guia_label = page.locator(
                'span.light-text:has-text("Estado de la guía:")'
            )
            
            if estado_guia_label.count() > 0:
                # Buscar el siguiente hermano span
                parent = estado_guia_label.locator('xpath=..')
                estado_span = parent.locator(
                    'span.strong-text.title'
                ).first
                
                if estado_span.count() > 0:
                    estado = estado_span.inner_text(timeout=5000)
                    return estado.strip()
            
            logging.warning("No se encontró el estado con ninguna estrategia")
            return ""

        except Exception as e:
            logging.error("Error al extraer estado: %s", e)
            return ""

    def close(self):
        """Cierra el browser y limpia recursos."""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, '_pw') and self._pw:
                self._pw.stop()
            logging.info("Scraper de Coordinadora cerrado correctamente")
        except Exception as e:
            logging.error("Error al cerrar scraper: %s", e)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
