"""
Scraper Web Async para Coordinadora con concurrencia.

Este módulo maneja el scraping concurrente de estados de Coordinadora
usando Playwright async para procesar múltiples guías en paralelo.

Responsabilidades:
- Scraping concurrente usando URL directa con ID de guía
- Control de concurrencia (máximo N ventanas simultáneas)
- Extracción de estado desde elemento HTML específico
- Manejo de timeouts y errores por guía

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import asyncio
import logging
from contextlib import suppress
from typing import List, Tuple

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError
)


class AsyncCoordinadoraScraper:
    """
    Scraper asíncrono para obtener estados de Coordinadora con concurrencia.
    
    Utiliza acceso directo a URL con el ID de la guía:
    https://coordinadora.com/rastreo/rastreo-de-guia/detalle-de-rastreo-de-guia/?guia=ID
    
    Procesa múltiples guías en paralelo con control de concurrencia.
    """

    def __init__(
        self,
        headless: bool = True,
        max_concurrency: int = 5,
        base_url: str = "",
        timeout_ms: int = 30000
    ):
        """
        Inicializa el scraper asíncrono de Coordinadora.
        
        Args:
            headless: Si True, ejecuta sin interfaz gráfica
            max_concurrency: Número máximo de páginas concurrentes
            base_url: URL base para construir las URLs de tracking
            timeout_ms: Timeout en milisegundos
        """
        self._headless = headless
        self._max_concurrency = max(1, int(max_concurrency))
        self._base_url = base_url
        self._timeout = int(timeout_ms)
        self._pw = None
        self.browser = None
        self._sem = asyncio.Semaphore(self._max_concurrency)
        
        logging.info(
            "AsyncCoordinadoraScraper inicializado. "
            "concurrencia=%d, headless=%s",
            self._max_concurrency,
            headless
        )

    async def start(self):
        """Inicia Playwright y el browser."""
        logging.info("Iniciando async_playwright...")
        self._pw = await async_playwright().start()
        
        logging.info(
            "Lanzando Chromium. headless=%s, concurrencia=%d",
            self._headless,
            self._max_concurrency
        )
        
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        
        if not self._headless:
            launch_args.append("--start-maximized")
        
        self.browser = await self._pw.chromium.launch(
            headless=self._headless,
            args=launch_args
        )
        
        logging.info("Chromium lanzado exitosamente")

    async def close(self):
        """Cierra el browser y Playwright."""
        with suppress(Exception):
            if self.browser:
                logging.info("Cerrando browser...")
                await self.browser.close()
        with suppress(Exception):
            if self._pw:
                logging.info("Deteniendo async_playwright...")
                await self._pw.stop()

    async def _extract_status_from_page(self, page) -> str:
        """
        Extrae el estado del paquete desde la página.
        
        Busca el elemento con las estrategias definidas.
        
        Args:
            page: Página de Playwright
            
        Returns:
            Estado extraído o string vacío
        """
        try:
            # Esperar carga básica
            with suppress(PlaywrightTimeoutError):
                await page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=self._timeout
                )
            
            # Estrategia 1: Buscar "Estado del paquete"
            try:
                estado_paquete = page.locator(
                    'span.strong-text.title:has-text("Estado del paquete")'
                )
                await estado_paquete.wait_for(
                    state="visible",
                    timeout=self._timeout
                )
                
                # Buscar el padre y extraer el segundo span
                parent = estado_paquete.locator('xpath=ancestor::div[1]')
                spans = parent.locator('span.strong-text.title')
                
                count = await spans.count()
                if count >= 2:
                    estado = await spans.nth(1).inner_text(timeout=5000)
                    return estado.strip()
            except PlaywrightTimeoutError:
                pass
            
            # Estrategia 2: Buscar en div.detail
            try:
                detail_div = page.locator(
                    'div.detail:has(span.light-text:'
                    'has-text("Estado de la guía:"))'
                )
                await detail_div.wait_for(
                    state="visible",
                    timeout=min(10000, self._timeout)
                )
                
                estado_span = detail_div.locator(
                    'span.strong-text.title'
                ).first
                
                if await estado_span.count() > 0:
                    estado = await estado_span.inner_text(timeout=5000)
                    return estado.strip()
            except PlaywrightTimeoutError:
                pass
            
            # Estrategia 3: Búsqueda general
            try:
                estado_label = page.locator(
                    'span.light-text:has-text("Estado de la guía:")'
                )
                await estado_label.wait_for(
                    state="visible",
                    timeout=min(8000, self._timeout)
                )
                
                parent = estado_label.locator('xpath=..')
                estado_span = parent.locator('span.strong-text.title').first
                
                if await estado_span.count() > 0:
                    estado = await estado_span.inner_text(timeout=5000)
                    return estado.strip()
            except PlaywrightTimeoutError:
                pass
            
            logging.warning(
                "No se encontró el estado con ninguna estrategia"
            )
            return ""
            
        except Exception as e:
            logging.error("Error al extraer estado: %s", e)
            return ""

    async def get_status(self, tracking_number: str) -> str:
        """
        Obtiene el estado de una guía de Coordinadora.
        
        Args:
            tracking_number: Número de guía a consultar
            
        Returns:
            Estado extraído o string vacío si hay error
        """
        # Control de concurrencia
        async with self._sem:
            context = None
            page = None
            
            try:
                # Crear nuevo contexto
                if self._headless:
                    context = await self.browser.new_context(
                        viewport={"width": 1920, "height": 1080}
                    )
                else:
                    context = await self.browser.new_context(viewport=None)
                
                page = await context.new_page()
                
                # Construir URL
                url = f"{self._base_url}{tracking_number}"
                
                logging.info("[%s] Navegando a URL...", tracking_number)
                
                # Navegar
                await page.goto(
                    url,
                    timeout=max(45000, self._timeout),
                    wait_until="domcontentloaded"
                )
                
                # Esperar carga
                await page.wait_for_timeout(2000)
                
                # Cerrar banners de cookies
                with suppress(Exception):
                    cookie_btn = page.locator(
                        'button:has-text("Aceptar"), '
                        'button:has-text("Acepto")'
                    ).first
                    
                    if await cookie_btn.is_visible(timeout=2000):
                        await cookie_btn.click(timeout=2000)
                
                # Extraer estado
                estado = await self._extract_status_from_page(page)
                
                if estado:
                    logging.info("[%s] Estado: %s", tracking_number, estado)
                else:
                    logging.warning(
                        "[%s] No se pudo extraer estado",
                        tracking_number
                    )
                
                return estado
                
            except PlaywrightTimeoutError as e:
                logging.error("[%s] Timeout: %s", tracking_number, e)
                return ""
            except Exception as e:
                logging.error("[%s] Error: %s", tracking_number, e)
                return ""
            finally:
                with suppress(Exception):
                    if page:
                        await page.close()
                with suppress(Exception):
                    if context:
                        await context.close()

    async def get_status_many(
        self,
        tracking_numbers: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Obtiene estados de múltiples guías en paralelo.
        
        Args:
            tracking_numbers: Lista de números de guía
            
        Returns:
            Lista de tuplas (tracking_number, estado)
        """
        logging.info(
            "Procesando %d guías con concurrencia=%d",
            len(tracking_numbers),
            self._max_concurrency
        )
        
        # Crear tareas concurrentes
        tasks = [
            self.get_status(tn) for tn in tracking_numbers
        ]
        
        # Ejecutar todas en paralelo (con límite de semáforo)
        results = await asyncio.gather(*tasks)
        
        # Combinar con tracking numbers
        return list(zip(tracking_numbers, results))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        asyncio.run(self.close())
