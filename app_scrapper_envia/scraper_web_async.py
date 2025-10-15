from __future__ import annotations
import asyncio
import logging
import re
from contextlib import suppress
from typing import Iterable, List, Tuple

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError
)


class AsyncEnviaScraper:
    """Async Playwright scraper for Envía via 17track.net with batch processing.

    - Processes up to 40 tracking numbers at once in a textarea
    - Results load in the same page (no new tab)
    - Extracts status from multiple result cards
    - Status format: "En tránsito (2 Días)" -> extract only "En tránsito"
    """

    def __init__(
        self,
        headless: bool = True,
        max_concurrency: int = 3,
        slow_mo: int = 0,
        retries: int = 2,
        timeout_ms: int = 30000,
        block_resources: bool = True,
        batch_size: int = 40
    ):
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

        # Args para evitar detección de bot
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]

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
        # Remove patterns like (X Días), (X días), etc.
        cleaned = re.sub(r'\s*\(\d+\s+[Dd]ías?\)', '', status_text)
        return cleaned.strip()

    async def _extract_results_from_page(
        self,
        page
    ) -> List[Tuple[str, str]]:
        """
        Extract all tracking results from the page.
        Returns list of (tracking_id, status) tuples.
        """
        results: List[Tuple[str, str]] = []

        try:
            # Wait for results to load - give time for dynamic content
            logging.debug("[PW] Waiting for results to load...")
            await asyncio.sleep(3)  # Wait for content to render

            # Find all result containers using more generic selector
            # Try multiple selectors in case page structure varies
            result_divs = page.locator(
                'div.flex.items-center.gap-2:has(span.text-sm.font-medium.truncate)'
            )

            count = await result_divs.count()
            logging.info("[PW] Found %d result divs", count)

            if count == 0:
                # Fallback: try broader selector
                logging.debug("[PW] Trying fallback selector...")
                result_divs = page.locator(
                    'div:has(span[title]):has(div.text-sm.text-text-primary)'
                )
                count = await result_divs.count()
                logging.info("[PW] Fallback found %d result divs", count)

            for i in range(count):
                try:
                    div = result_divs.nth(i)

                    # Extract tracking ID from title attribute or text
                    id_locator = div.locator(
                        'span.text-sm.font-medium.truncate'
                    )
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
                        "[PW] Error extracting result %d: %s",
                        i,
                        e
                    )
                    continue

        except Exception as e:
            logging.error("[PW] Error extracting results: %s", e)

        return results

    async def get_status_batch(
        self,
        tracking_numbers: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Process a batch of up to 40 tracking numbers.
        Returns list of (tracking_id, status) tuples.
        """
        context = None
        page = None

        try:
            # Create new context with headers and settings
            if self._headless:
                logging.debug("[PW] Creating new context (headless)")
                context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    locale="es-ES",
                    timezone_id="America/Bogota",
                    extra_http_headers={
                        "Accept": (
                            "text/html,application/xhtml+xml,"
                            "application/xml;q=0.9,image/avif,"
                            "image/webp,image/apng,*/*;q=0.8,"
                            "application/signed-exchange;v=b3;q=0.7"
                        ),
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0",
                    }
                )
            else:
                logging.debug("[PW] Creating new context (headed)")
                context = await self.browser.new_context(
                    viewport=None,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    locale="es-ES",
                    timezone_id="America/Bogota",
                    extra_http_headers={
                        "Accept": (
                            "text/html,application/xhtml+xml,"
                            "application/xml;q=0.9,image/avif,"
                            "image/webp,image/apng,*/*;q=0.8"
                        ),
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )

            # Block heavy resources to speed up
            if self._block_resources:
                async def _route_handler(route):
                    try:
                        resource_type = route.request.resource_type
                        if resource_type in {
                            "image", "media", "font"
                        }:
                            await route.abort()
                        else:
                            await route.continue_()
                    except Exception:
                        with suppress(Exception):
                            await route.continue_()

                logging.debug("[PW] Installing route handler")
                await context.route("**/*", _route_handler)

            logging.info(
                "[PW] Processing batch of %d tracking numbers",
                len(tracking_numbers)
            )
            page = await context.new_page()

            # Ocultar propiedades de automatización
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
            """)

            # Set additional headers on the page
            await page.set_extra_http_headers({
                "Referer": "https://www.google.com/",
            })

            # Navigate to 17track Envía page
            url = "https://www.17track.net/es/carriers/env%C3%ADa-envia"
            logging.debug("[PW] Navigating to %s", url)
            await page.goto(
                url,
                timeout=max(45000, self._timeout),
                wait_until="networkidle"  # Esperar a que la red esté inactiva
            )

            # Wait for page to fully render
            logging.debug("[PW] Waiting for page to render...")
            await asyncio.sleep(3)

            # Try to accept cookie banners
            with suppress(Exception):
                # Try multiple cookie button selectors
                cookie_selectors = [
                    'button:has-text("Aceptar")',
                    'button:has-text("Accept")',
                    'button:has-text("Acepto")',
                    '[class*="accept"]',
                    '[class*="cookie"] button'
                ]
                for selector in cookie_selectors:
                    try:
                        cookie_btn = page.locator(selector).first
                        await cookie_btn.click(timeout=2000)
                        logging.debug("[PW] Cookie banner clicked")
                        break
                    except:
                        continue

            # Wait a bit after cookie
            await asyncio.sleep(1)

            # Find the textarea con el selector EXACTO
            logging.debug("[PW] Looking for textarea...")
            textarea = page.locator(
                'textarea#auto-size-textarea.batch_track_textarea__rhhSa'
            )

            try:
                await textarea.wait_for(state="visible", timeout=15000)
                logging.info("[PW] Textarea found!")
            except Exception as e:
                logging.error("[PW] Textarea not found: %s", e)
                # Try fallback selectors
                fallback_selectors = [
                    'textarea#auto-size-textarea',
                    'textarea[class*="batch_track_textarea"]',
                    'textarea[placeholder*="40"]'
                ]
                for selector in fallback_selectors:
                    try:
                        textarea = page.locator(selector).first
                        await textarea.wait_for(state="visible", timeout=5000)
                        logging.info(
                            "[PW] Textarea found with fallback: %s",
                            selector
                        )
                        break
                    except:
                        continue
                else:
                    raise Exception("No se encontró el textarea")

            await textarea.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

            # Clear and fill textarea
            await textarea.click()
            await textarea.fill("")
            batch_text = "\n".join(tracking_numbers[:40])
            await textarea.fill(batch_text)
            logging.info(
                "[PW] Filled %d tracking numbers in textarea",
                len(tracking_numbers)
            )

            # Wait a bit after filling
            await asyncio.sleep(1)

            # Find and click the Rastrear button - SELECTOR EXACTO
            logging.debug("[PW] Looking for Rastrear button...")
            track_button = page.locator(
                'div.batch_track_search-area-bottom__MV_vI:has-text("Rastrear")'
            )

            try:
                await track_button.wait_for(state="visible", timeout=10000)
                logging.info("[PW] Rastrear button found!")
            except Exception as e:
                logging.error("[PW] Button not found: %s", e)
                # Try fallback selectors
                fallback_buttons = [
                    'div.btn-primary:has-text("Rastrear")',
                    'div[class*="search-area-bottom"]:has-text("Rastrear")',
                    'div.btn:has-text("Rastrear")',
                    'button:has-text("Rastrear")'
                ]
                for selector in fallback_buttons:
                    try:
                        track_button = page.locator(selector).first
                        await track_button.wait_for(
                            state="visible",
                            timeout=5000
                        )
                        logging.info(
                            "[PW] Button found with fallback: %s",
                            selector
                        )
                        break
                    except:
                        continue
                else:
                    # Last resort: press Enter on textarea
                    logging.warning(
                        "[PW] No button found, pressing Enter on textarea"
                    )
                    await textarea.press("Enter")
                    await asyncio.sleep(1)
                    track_button = None

            if track_button:
                await track_button.click()
                logging.info("[PW] Clicked Rastrear button")

            # Wait for results to load
            logging.info("[PW] Waiting for results to load...")
            await asyncio.sleep(8)  # Dar tiempo para que carguen resultados

            # Extract all results
            results = await self._extract_results_from_page(page)

            logging.info(
                "[PW] Batch complete: %d results extracted",
                len(results)
            )

            # Fill missing results with empty status
            result_dict = dict(results)
            complete_results = []
            for tn in tracking_numbers:
                status = result_dict.get(tn, "")
                complete_results.append((tn, status))

            return complete_results

        except Exception as e:
            logging.error("[PW] Error processing batch: %s", e)
            # Return empty results for all tracking numbers
            return [(tn, "") for tn in tracking_numbers]

        finally:
            with suppress(Exception):
                if page:
                    await page.close()
            with suppress(Exception):
                if context:
                    await context.close()

    async def get_status_many(
        self,
        tracking_numbers: Iterable[str],
        rps: float | None = None
    ) -> List[Tuple[str, str]]:
        """
        Process multiple tracking numbers in batches of up to 40.

        Args:
            tracking_numbers: Iterable of tracking numbers to process
            rps: Requests per second limit (not used in batch mode)

        Returns:
            List of (tracking_number, status) tuples
        """
        results: List[Tuple[str, str]] = []
        tn_list = list(tracking_numbers)

        # Split into batches of 40
        batches = []
        for i in range(0, len(tn_list), self._batch_size):
            batch = tn_list[i:i + self._batch_size]
            batches.append(batch)

        logging.info(
            "[PW] Processing %d tracking numbers in %d batches",
            len(tn_list),
            len(batches)
        )

        # Process batches with concurrency control
        async def process_batch(batch: List[str], batch_num: int):
            async with self._sem:
                logging.info(
                    "[PW] Starting batch %d/%d (%d items)",
                    batch_num + 1,
                    len(batches),
                    len(batch)
                )

                # Retry logic for batch
                for attempt in range(self._retries + 1):
                    batch_results = await self.get_status_batch(batch)

                    # Check if we got meaningful results
                    success_count = sum(
                        1 for _, status in batch_results if status
                    )

                    if success_count > 0 or attempt == self._retries:
                        results.extend(batch_results)
                        logging.info(
                            "[PW] Batch %d complete: "
                            "%d/%d successful",
                            batch_num + 1,
                            success_count,
                            len(batch)
                        )
                        break

                    if attempt < self._retries:
                        delay = 2 * (attempt + 1)
                        logging.warning(
                            "[PW] Batch %d failed, "
                            "retrying after %ds",
                            batch_num + 1,
                            delay
                        )
                        await asyncio.sleep(delay)

        # Process all batches
        tasks = [
            process_batch(batch, i)
            for i, batch in enumerate(batches)
        ]
        await asyncio.gather(*tasks)

        return results
