from __future__ import annotations
import asyncio
import logging
import re
from contextlib import suppress
from typing import Iterable, List, Tuple

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class AsyncEnviaScraper:
    """Async Playwright scraper for Envía via 17track.net with batch processing.

    - Processes up to 40 tracking numbers at once in a textarea
    - Results load in the same page (no new tab)
    - Extracts status from multiple result cards
    - Status format: "En tránsito (2 Días)" -> extract only "En tránsito"
    """

    def __init__(self, headless: bool = True, max_concurrency: int = 3, slow_mo: int = 0,
                 retries: int = 2, timeout_ms: int = 30000, block_resources: bool = True,
                 batch_size: int = 40):
        self._headless = headless
        self._max_concurrency = max(1, int(max_concurrency))
        self._slow_mo = slow_mo if headless else max(slow_mo, 100)
        self._retries = max(0, int(retries))
        self._timeout = int(timeout_ms)
        self._block_resources = block_resources
        self._batch_size = min(batch_size, 40)  # Max 40 per batch
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
        self.browser = await self._pw.chromium.launch(
            headless=self._headless,
            slow_mo=self._slow_mo,
            args=launch_args
        )
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

    def _clean_status(self, status_text: str) -> str:
        """Remove time indicators like '(2 Días)' from status."""
        import re
        # Remove patterns like (X Días), (X días), etc.
        cleaned = re.sub(r'\s*\(\d+\s+[Dd]ías?\)', '', status_text)
        return cleaned.strip()

    async def _extract_results_from_page(self, page) -> List[Tuple[str, str]]:
        """
        Extract all tracking results from the page.
        Returns list of (tracking_id, status) tuples.
        """
        results: List[Tuple[str, str]] = []

        try:
            # Wait for results to load
            logging.debug("[PW] Waiting for results to load...")
            await asyncio.sleep(2)  # Give page time to render results

            # Find all result containers
            # Using the parent div class from your example
            result_divs = page.locator(
                'div.flex.items-center.gap-2.w-\\[310px\\].p-1\\.5'
            )

            count = await result_divs.count()
            logging.info("[PW] Found %d result divs", count)

            for i in range(count):
                try:
                    div = result_divs.nth(i)

                    # Extract tracking ID
                    id_locator = div.locator(
                        'span.text-sm.font-medium.truncate')
                    tracking_id = await id_locator.get_attribute('title')

                    if not tracking_id:
                        tracking_id = await id_locator.inner_text()

                    tracking_id = tracking_id.strip()

                    # Extract status (without time)
                    status_locator = div.locator(
                        'div.text-sm.text-text-primary.flex.items-center.gap-1'
                    )
                    status_text = await status_locator.inner_text()
                    status_text = self._clean_status(status_text)

                    if tracking_id and status_text:
                        results.append((tracking_id, status_text))
                        logging.debug(
                            "[PW] Extracted: %s -> %s",
                            tracking_id,
                            status_text
                        )

                except Exception as e:
                    logging.warning(
                        "[PW] Error extracting result %d: %s", i, e)
                    continue

        except Exception as e:
            logging.error("[PW] Error extracting results: %s", e)

        return results
        return txt3
        return ""

    async def get_status(self, tracking_number: str) -> str:
        context = None
        page = None
        popup = None
        try:
            # New context per guide
            if self._headless:
                logging.debug(
                    "[PW] Creating new context (headless) for %s", tracking_number)
                context = await self.browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                logging.debug(
                    "[PW] Creating new context (headed) for %s", tracking_number)
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
                logging.debug(
                    "[PW] Installing route handler (resource blocking)")
                await context.route("**/*", _route_handler)

            logging.info("[PW] [%-14s] New page", tracking_number)
            page = await context.new_page()
            logging.debug(
                "[PW] [%s] Navigating to tracking page", tracking_number)
            await page.goto("https://interrapidisimo.com/sigue-tu-envio/", timeout=max(45000, self._timeout), wait_until="domcontentloaded")

            # Try to accept cookie banners quickly
            with suppress(Exception):
                btn = page.get_by_role("button", name=lambda n: n and (
                    "acept" in n.lower() or "de acuerdo" in n.lower() or "entendido" in n.lower()))
                await btn.click(timeout=2000)
                logging.debug(
                    "[PW] [%s] Cookie banner clicked", tracking_number)

            # Find the visible input (desktop/mobile)
            input_css = "#inputGuide:visible, #inputGuideMovil:visible, input.buscarGuiaInput:visible"
            loc = page.locator(input_css).first
            logging.debug(
                "[PW] [%s] Waiting for input visible", tracking_number)
            await loc.wait_for(state="visible", timeout=self._timeout)
            await loc.scroll_into_view_if_needed()
            with suppress(Exception):
                await loc.fill("")
            await loc.fill(tracking_number)
            logging.debug("[PW] [%s] Tracking typed", tracking_number)

            # Follow new page created by Enter
            try:
                logging.debug(
                    "[PW] [%s] Expecting popup on Enter", tracking_number)
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
            logging.debug("[PW] [%s] Extracting status from %s",
                          tracking_number, "popup" if popup else "page")
            result = await self._extract_status_from_page(target)
            logging.info("[PW] [%-14s] Status: %s",
                         tracking_number, result or "<empty>")
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
                        logging.info(
                            "[PW] [%-14s] Done in %d attempts", tn, attempt + 1)
                        break
                    if attempt < self._retries:
                        logging.debug(
                            "[PW] [%-14s] Empty, retrying after %.2fs", tn, delay)
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
            logging.info("[PW] Scheduling %d tasks with RPS=%.2f (interval=%.3fs)", len(
                list(tracking_numbers)), rps, interval)
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
            logging.info(
                "[PW] Launching %d tasks immediately (no RPS throttling)", len(tn_list))
            tasks = [asyncio.create_task(worker(tn)) for tn in tn_list]

        await asyncio.gather(*tasks)
        return results
