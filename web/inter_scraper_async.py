from __future__ import annotations
import asyncio
import logging
from contextlib import suppress
from typing import Iterable, List, Tuple

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class AsyncInterScraper:
    """Async Playwright scraper for Interrapidísimo with concurrency control.

    - Strictly reads the status from the detail card:
      div.content p.title-current-state + p.font-weight-600
    - Follows the new tab created after entering the tracking number.
    - Exposes get_status_many to process multiple guides concurrently.
    """

    def __init__(self, headless: bool = True, max_concurrency: int = 3, slow_mo: int = 0):
        self._headless = headless
        self._max_concurrency = max(1, int(max_concurrency))
        self._slow_mo = slow_mo if headless else max(slow_mo, 100)
        self._pw = None
        self.browser = None
        self._sem = asyncio.Semaphore(self._max_concurrency)

    async def start(self):
        self._pw = await async_playwright().start()
        logging.info("Launching Playwright Chromium (async). headless=%s", self._headless)
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
        if not self._headless:
            launch_args.append("--start-maximized")
        self.browser = await self._pw.chromium.launch(headless=self._headless, slow_mo=self._slow_mo, args=launch_args)

    async def close(self):
        with suppress(Exception):
            if self.browser:
                await self.browser.close()
        with suppress(Exception):
            if self._pw:
                await self._pw.stop()

    async def _extract_status_from_page(self, page) -> str:
        # Wait basic load
        with suppress(PlaywrightTimeoutError):
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        # Anchor to the title and read the following bold text
        try:
            title = page.locator("css=div.content p.title-current-state").first
            await title.wait_for(state="visible", timeout=15000)
            value = title.locator("xpath=following-sibling::p[contains(@class,'font-weight-600')][1]")
            await value.wait_for(state="visible", timeout=15000)
            txt = (await value.inner_text()).strip()
            if txt:
                return txt
        except PlaywrightTimeoutError:
            pass
        # Direct CSS fallback within the same content card
        with suppress(Exception):
            value2 = page.locator("css=div.content p.font-weight-600").first
            await value2.wait_for(state="visible", timeout=5000)
            txt2 = (await value2.inner_text()).strip()
            if txt2:
                return txt2
        # Last resort: novelty pill
        with suppress(Exception):
            novelty = page.locator("css=p.guide-WhitOut-Novelty").first
            await novelty.wait_for(state="visible", timeout=3000)
            txt3 = (await novelty.inner_text()).strip()
            if txt3:
                return txt3
        return ""

    async def get_status(self, tracking_number: str) -> str:
        context = None
        page = None
        popup = None
        try:
            # New context per guide
            if self._headless:
                context = await self.browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                context = await self.browser.new_context(viewport=None)
            page = await context.new_page()
            await page.goto("https://interrapidisimo.com/sigue-tu-envio/", timeout=45000, wait_until="domcontentloaded")

            # Try to accept cookie banners quickly
            with suppress(Exception):
                btn = page.get_by_role("button", name=lambda n: n and ("acept" in n.lower() or "de acuerdo" in n.lower() or "entendido" in n.lower()))
                await btn.click(timeout=2000)

            # Find the visible input (desktop/mobile)
            input_css = "#inputGuide:visible, #inputGuideMovil:visible, input.buscarGuiaInput:visible"
            loc = page.locator(input_css).first
            await loc.wait_for(state="visible", timeout=15000)
            await loc.scroll_into_view_if_needed()
            with suppress(Exception):
                await loc.fill("")
            await loc.fill(tracking_number)

            # Follow new page created by Enter
            try:
                async with context.expect_page(timeout=20000) as new_page_info:
                    await loc.press("Enter")
                popup = await new_page_info.value
                with suppress(Exception):
                    await popup.bring_to_front()
            except PlaywrightTimeoutError:
                popup = None
                with suppress(PlaywrightTimeoutError):
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)

            target = popup if popup is not None else page
            return await self._extract_status_from_page(target)
        except Exception as e:
            logging.error("Async scraper error for %s: %s", tracking_number, e)
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

    async def get_status_many(self, tracking_numbers: Iterable[str]) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []

        async def worker(tn: str):
            async with self._sem:
                status = await self.get_status(tn)
                results.append((tn, status))

        await asyncio.gather(*(worker(tn) for tn in tracking_numbers))
        return results
