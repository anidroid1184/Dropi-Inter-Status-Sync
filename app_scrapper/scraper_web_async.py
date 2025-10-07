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

    def __init__(self, headless: bool = True, max_concurrency: int = 3, slow_mo: int = 0,
                 retries: int = 2, timeout_ms: int = 30000, block_resources: bool = True):
        self._headless = headless
        self._max_concurrency = max(1, int(max_concurrency))
        self._slow_mo = slow_mo if headless else max(slow_mo, 100)
        self._retries = max(0, int(retries))
        self._timeout = int(timeout_ms)
        self._block_resources = block_resources
        self._pw = None
        self.browser = None
        self._sem = asyncio.Semaphore(self._max_concurrency)

    async def start(self):
        logging.info("[PW] Starting async_playwright...")
        self._pw = await async_playwright().start()
        logging.info("[PW] Launching Chromium. headless=%s", self._headless)
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
        if not self._headless:
            launch_args.append("--start-maximized")
        self.browser = await self._pw.chromium.launch(headless=self._headless, slow_mo=self._slow_mo, args=launch_args)
        logging.info("[PW] Chromium launched. slow_mo=%s", self._slow_mo)

    async def close(self):
        with suppress(Exception):
            if self.browser:
                logging.info("[PW] Closing browser...")
                await self.browser.close()
        with suppress(Exception):
            if self._pw:
                logging.info("[PW] Stopping async_playwright...")
                await self._pw.stop()

    async def _extract_status_from_page(self, page) -> str:
        # Wait basic load
        with suppress(PlaywrightTimeoutError):
            logging.debug("[PW] Waiting for DOMContentLoaded (timeout=%sms)", self._timeout)
            await page.wait_for_load_state("domcontentloaded", timeout=self._timeout)
        # Anchor to the title and read the following bold text
        try:
            title = page.locator("css=div.content p.title-current-state").first
            logging.debug("[PW] Waiting title-current-state visible")
            await title.wait_for(state="visible", timeout=self._timeout)
            value = title.locator("xpath=following-sibling::p[contains(@class,'font-weight-600')][1]")
            logging.debug("[PW] Waiting value (font-weight-600) visible")
            await value.wait_for(state="visible", timeout=self._timeout)
            txt = (await value.inner_text()).strip()
            if txt:
                logging.debug("[PW] Extracted status via primary locator: %s", txt)
                return txt
        except PlaywrightTimeoutError:
            pass
        # Alternative anchor: by text content of the title (class may vary)
        try:
            title_by_text = page.locator(
                "xpath=(//*[self::p or self::h1 or self::h2 or self::div][contains(normalize-space(.), 'Estado actual de tu envío')])[1]"
            )
            logging.debug("[PW] Waiting alternative title text visible")
            await title_by_text.wait_for(state="visible", timeout=min(6000, self._timeout))
            value = title_by_text.locator("xpath=following::p[contains(@class,'font-weight-600')][1]")
            logging.debug("[PW] Waiting value (alt) visible")
            await value.wait_for(state="visible", timeout=min(6000, self._timeout))
            txt = (await value.inner_text()).strip()
            if txt:
                logging.debug("[PW] Extracted status via alt locator: %s", txt)
                return txt
        except PlaywrightTimeoutError:
            pass
        # Direct CSS fallback within the same content card
        with suppress(Exception):
            value2 = page.locator("css=div.content p.font-weight-600").first
            logging.debug("[PW] Waiting fallback value visible")
            await value2.wait_for(state="visible", timeout=min(5000, self._timeout))
            txt2 = (await value2.inner_text()).strip()
            if txt2:
                logging.debug("[PW] Extracted status via fallback: %s", txt2)
                return txt2
        # Last resort: novelty pill
        with suppress(Exception):
            novelty = page.locator("css=p.guide-WhitOut-Novelty").first
            await novelty.wait_for(state="visible", timeout=min(3000, self._timeout))
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
                logging.debug("[PW] Creating new context (headless) for %s", tracking_number)
                context = await self.browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                logging.debug("[PW] Creating new context (headed) for %s", tracking_number)
                context = await self.browser.new_context(viewport=None)

            # Block heavy resources to speed up
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
                logging.debug("[PW] Installing route handler (resource blocking)")
                await context.route("**/*", _route_handler)

            logging.info("[PW] [%-14s] New page", tracking_number)
            page = await context.new_page()
            logging.debug("[PW] [%s] Navigating to tracking page", tracking_number)
            await page.goto("https://interrapidisimo.com/sigue-tu-envio/", timeout=max(45000, self._timeout), wait_until="domcontentloaded")

            # Try to accept cookie banners quickly
            with suppress(Exception):
                btn = page.get_by_role("button", name=lambda n: n and ("acept" in n.lower() or "de acuerdo" in n.lower() or "entendido" in n.lower()))
                await btn.click(timeout=2000)
                logging.debug("[PW] [%s] Cookie banner clicked", tracking_number)

            # Find the visible input (desktop/mobile)
            input_css = "#inputGuide:visible, #inputGuideMovil:visible, input.buscarGuiaInput:visible"
            loc = page.locator(input_css).first
            logging.debug("[PW] [%s] Waiting for input visible", tracking_number)
            await loc.wait_for(state="visible", timeout=self._timeout)
            await loc.scroll_into_view_if_needed()
            with suppress(Exception):
                await loc.fill("")
            await loc.fill(tracking_number)
            logging.debug("[PW] [%s] Tracking typed", tracking_number)

            # Follow new page created by Enter
            try:
                logging.debug("[PW] [%s] Expecting popup on Enter", tracking_number)
                async with context.expect_page(timeout=self._timeout) as new_page_info:
                    await loc.press("Enter")
                popup = await new_page_info.value
                with suppress(Exception):
                    await popup.bring_to_front()
                logging.debug("[PW] [%s] Popup opened", tracking_number)
            except PlaywrightTimeoutError:
                popup = None
                with suppress(PlaywrightTimeoutError):
                    await page.wait_for_load_state("domcontentloaded", timeout=self._timeout)

            target = popup if popup is not None else page
            logging.debug("[PW] [%s] Extracting status from %s", tracking_number, "popup" if popup else "page")
            result = await self._extract_status_from_page(target)
            logging.info("[PW] [%-14s] Status: %s", tracking_number, result or "<empty>")
            return result
        except Exception as e:
            logging.error("[PW] Error for %s: %s", tracking_number, e)
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

    async def get_status_many(self, tracking_numbers: Iterable[str], rps: float | None = None) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []

        async def worker(tn: str):
            async with self._sem:
                # Retries with backoff
                delay = 0.75
                for attempt in range(self._retries + 1):
                    logging.info("[PW] [%-14s] Attempt %d", tn, attempt + 1)
                    status = await self.get_status(tn)
                    if status:
                        results.append((tn, status))
                        logging.info("[PW] [%-14s] Done in %d attempts", tn, attempt + 1)
                        break
                    if attempt < self._retries:
                        logging.debug("[PW] [%-14s] Empty, retrying after %.2fs", tn, delay)
                        await asyncio.sleep(delay)
                        delay *= 2
                else:
                    # After retries, record empty string to keep row mapping intact
                    results.append((tn, ""))
                    logging.info("[PW] [%-14s] Empty after retries", tn)
        tasks = []
        if rps and rps > 0:
            interval = 1.0 / float(rps)
            start = asyncio.get_event_loop().time()
            logging.info("[PW] Scheduling %d tasks with RPS=%.2f (interval=%.3fs)", len(list(tracking_numbers)), rps, interval)
            # Need a snapshot since tracking_numbers may be a generator
            tn_list = list(tracking_numbers)
            for i, tn in enumerate(tracking_numbers):
                # Stagger task starts to respect RPS
                async def delayed_launch(tn=tn, i=i):
                    target_time = start + i * interval
                    now = asyncio.get_event_loop().time()
                    if target_time > now:
                        await asyncio.sleep(target_time - now)
                    await worker(tn)
                tasks.append(asyncio.create_task(delayed_launch()))
        else:
            tn_list = list(tracking_numbers)
            logging.info("[PW] Launching %d tasks immediately (no RPS throttling)", len(tn_list))
            tasks = [asyncio.create_task(worker(tn)) for tn in tn_list]

        await asyncio.gather(*tasks)
        return results
