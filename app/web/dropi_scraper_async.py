from __future__ import annotations
import asyncio
import logging
from contextlib import suppress
from typing import Iterable, List, Tuple, Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class AsyncDropiScraper:
    """Scraper genérico para el portal (tercero) usado por Dropi.

    Objetivo de esta primera versión:
    - Permitir pruebas headful (headless=False) para observar el flujo.
    - Parametrizar URL, selectores y si abre nueva pestaña.
    - Exponer un método get_status(...) para poder iterar múltiples guías.

    Una vez confirmemos los selectores definitivos, los dejaremos fijos aquí.
    """

    def __init__(
        self,
        headless: bool = False,
        max_concurrency: int = 2,
        slow_mo: int = 200,
        timeout_ms: int = 30000,
        block_resources: bool = False,
    ):
        self._headless = headless
        self._max_concurrency = max(1, int(max_concurrency))
        self._slow_mo = slow_mo if headless else max(slow_mo, 100)
        self._timeout = int(timeout_ms)
        self._block_resources = block_resources
        self._pw = None
        self.browser = None
        self._sem = asyncio.Semaphore(self._max_concurrency)

    async def start(self):
        self._pw = await async_playwright().start()
        logging.info("Launching Playwright Chromium (dropi). headless=%s", self._headless)
        args = ["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"]
        self.browser = await self._pw.chromium.launch(headless=self._headless, slow_mo=self._slow_mo, args=args)

    async def close(self):
        with suppress(Exception):
            if self.browser:
                await self.browser.close()
        with suppress(Exception):
            if self._pw:
                await self._pw.stop()

    async def _new_context(self):
        if self._headless:
            ctx = await self.browser.new_context(viewport={"width": 1440, "height": 900})
        else:
            ctx = await self.browser.new_context(viewport=None)
        if self._block_resources:
            async def _route_handler(route):
                try:
                    if route.request.resource_type in {"image", "media", "font", "stylesheet"}:
                        await route.abort()
                    else:
                        await route.continue_()
                except Exception:
                    with suppress(Exception):
                        await route.continue_()
            await ctx.route("**/*", _route_handler)
        return ctx

    async def get_status(
        self,
        tracking_number: str,
        url: str,
        search_selector: str,
        status_selector: Optional[str] = None,
        expect_new_page: bool = False,
    ) -> str:
        """Navega al portal, ingresa el tracking y devuelve el texto del estado.

        - url: URL del portal del tercero.
        - search_selector: selector del input de búsqueda (CSS, XPath o id simple).
        - status_selector: selector del elemento que contiene el estado (cuando esté claro).
        - expect_new_page: True si al buscar se abre una nueva pestaña.
        """
        context = None
        page = None
        popup = None
        try:
            context = await self._new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout)

            # Resolver el locator del input
            sel = search_selector.strip()
            if sel.startswith("//"):
                input_loc = page.locator(f"xpath={sel}")
            elif sel.startswith("#") or sel.startswith("."):
                input_loc = page.locator(sel)
            else:
                input_loc = page.locator(f"#{sel}")

            await input_loc.wait_for(timeout=self._timeout)
            await input_loc.fill("")
            await input_loc.type(tracking_number, delay=20)

            try:
                if expect_new_page:
                    async with context.expect_page(timeout=self._timeout) as new_page_info:
                        await input_loc.press("Enter")
                    popup = await new_page_info.value
                    await popup.wait_for_load_state("domcontentloaded", timeout=self._timeout)
                else:
                    await input_loc.press("Enter")
                    await page.wait_for_load_state("domcontentloaded", timeout=self._timeout)
            except PlaywrightTimeoutError:
                pass

            target = popup if popup is not None else page

            if status_selector:
                # Resolver el locator del estado
                ssel = status_selector.strip()
                if ssel.startswith("//"):
                    status_loc = target.locator(f"xpath={ssel}")
                elif ssel.startswith("#") or ssel.startswith("."):
                    status_loc = target.locator(ssel)
                else:
                    status_loc = target.locator(f"#{ssel}")
                try:
                    await status_loc.wait_for(timeout=self._timeout)
                    text = (await status_loc.first.inner_text()).strip()
                    return text
                except PlaywrightTimeoutError:
                    return ""
            # Si aún no tenemos selector, devolvemos vacío y dejamos observar manualmente
            return ""
        except Exception as e:
            logging.error("Dropi scraper error for %s: %s", tracking_number, e)
            return ""
        finally:
            with suppress(Exception):
                if popup:
                    await popup.close()
            with suppress(Exception):
                if page:
                    await page.close()
            with suppress(Exception):
                if context:
                    await context.close()

    async def get_status_many(
        self,
        tracking_numbers: Iterable[str],
        url: str,
        search_selector: str,
        status_selector: Optional[str] = None,
        expect_new_page: bool = False,
        rps: float | None = None,
    ) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []

        async def worker(tn: str):
            async with self._sem:
                text = await self.get_status(tn, url, search_selector, status_selector, expect_new_page)
                results.append((tn, text))

        tasks = []
        if rps and rps > 0:
            interval = 1.0 / float(rps)
            start = asyncio.get_event_loop().time()
            for i, tn in enumerate(tracking_numbers):
                async def delayed_launch(tn=tn, i=i):
                    target_time = start + i * interval
                    now = asyncio.get_event_loop().time()
                    if target_time > now:
                        await asyncio.sleep(target_time - now)
                    await worker(tn)
                tasks.append(asyncio.create_task(delayed_launch()))
        else:
            tasks = [asyncio.create_task(worker(tn)) for tn in tracking_numbers]

        await asyncio.gather(*tasks)
        return results
