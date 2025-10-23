from __future__ import annotations
import logging
import re
from contextlib import suppress
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)
from typing import List, Tuple


class EnviaScraper:
    """Playwright-based scraper to fetch tracking status from Envía via 17track.

    This implementation processes tracking numbers in batches of up to 40
    using the batch tracking interface at 17track.net. Status text is returned
    RAW (without time indicators like '(2 Días)').

    Normalization is handled elsewhere by TrackerService using JSON mappings.
    """

    def __init__(self, headless: bool = True, batch_size: int = 40):
        self._pw = sync_playwright().start()
        self._headless = headless
        self._batch_size = min(batch_size, 40)  # Max 40 per batch
        logging.info("Launching Playwright Chromium. headless=%s", headless)

        # Args para evitar detección de bot
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
        ]
        slow_mo = 250 if not headless else 0
        if not headless:
            launch_args.append("--start-maximized")

        self.browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=launch_args,
        )

    def _format_tracking_number(self, tracking_number: str) -> str:
        """
        Format tracking number as XXX-XXXXXXXXXX (3 digits, hyphen, rest).
        Preserves leading zeros.
        Example: 014152617422 -> 014-152617422
        """
        # Remover cualquier guion existente y espacios
        clean_number = tracking_number.strip().replace("-", "").replace(" ", "")

        # Si tiene al menos 4 dígitos, formatear como XXX-resto
        if len(clean_number) >= 4:
            return f"{clean_number[:3]}-{clean_number[3:]}"

        # Si es muy corto, devolver sin cambios
        return clean_number

    def _clean_status(self, status_text: str) -> str:
        """Remove time indicators like '(2 Días)' from status."""
        # Remove patterns like (X Días), (X días), etc.
        cleaned = re.sub(r'\s*\(\d+\s+[Dd]ías?\)', '', status_text)
        return cleaned.strip()

    def get_status(self, tracking_number: str) -> str:
        """
        Get status for a single tracking number.
        Uses batch processing with just one number.
        """
        results = self.get_status_batch([tracking_number])
        if results and len(results) > 0:
            return results[0][1]
        return ""

    def get_status_batch(
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
            # Create new context with headers
            if self._headless:
                context = self.browser.new_context(
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
                            "application/xml;q=0.9,image/webp,*/*;q=0.8"
                        ),
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )
            else:
                context = self.browser.new_context(
                    viewport=None,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    locale="es-ES",
                    timezone_id="America/Bogota",
                )

            page = context.new_page()

            # Ocultar propiedades de automatización
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en']
                });
                window.chrome = { runtime: {} };
            """)

            # Set referer
            page.set_extra_http_headers({
                "Referer": "https://www.google.com/",
            })

            # Navigate to 17track Envía page
            url = "https://www.17track.net/es/carriers/env%C3%ADa-envia"
            logging.info(
                "Processing batch of %d tracking numbers",
                len(tracking_numbers)
            )
            page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Wait for page to fully render and load dynamic content
            page.wait_for_timeout(5000)

            # Try to accept cookie banners
            with suppress(Exception):
                cookie_selectors = [
                    'button:has-text("Aceptar")',
                    'button:has-text("Accept")',
                    '[class*="accept"]'
                ]
                for selector in cookie_selectors:
                    try:
                        cookie_btn = page.locator(selector).first
                        cookie_btn.click(timeout=2000)
                        logging.debug("Cookie banner clicked")
                        break
                    except:
                        continue

            page.wait_for_timeout(1000)

            # Find the textarea con selector EXACTO
            logging.info("Looking for textarea...")
            textarea = page.locator(
                'textarea#auto-size-textarea.batch_track_textarea__rhhSa'
            )

            try:
                textarea.wait_for(state="visible", timeout=15000)
                logging.info("Textarea found!")
            except Exception as e:
                logging.error(f"Textarea not found: {e}")
                # Try fallback
                fallback_selectors = [
                    'textarea#auto-size-textarea',
                    'textarea[class*="batch_track_textarea"]',
                    'textarea[placeholder*="40"]'
                ]
                for selector in fallback_selectors:
                    try:
                        textarea = page.locator(selector).first
                        textarea.wait_for(state="visible", timeout=5000)
                        logging.info(
                            f"Textarea found with fallback: {selector}")
                        break
                    except:
                        continue
                else:
                    raise Exception("No se encontró el textarea")

            textarea.scroll_into_view_if_needed()
            page.wait_for_timeout(500)

            # Preparar texto del batch (sin formato, números tal cual)
            batch_text = "\n".join(tracking_numbers[:40])

            # Método 1: Intentar con JavaScript (más confiable)
            logging.debug("Filling textarea with JavaScript...")
            try:
                textarea.evaluate(
                    """(element, text) => {
                        element.value = text;
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    batch_text
                )
                logging.info(
                    f"Filled {len(tracking_numbers)} tracking numbers via JavaScript"
                )
            except Exception as e:
                logging.warning(
                    f"JavaScript fill failed: {e}, trying click+fill")
                # Método 2: Click + fill tradicional
                try:
                    textarea.click()
                    page.wait_for_timeout(300)
                    textarea.fill("")
                    page.wait_for_timeout(300)
                    textarea.fill(batch_text)
                    logging.info(
                        f"Filled {len(tracking_numbers)} tracking numbers via click+fill"
                    )
                except Exception as e2:
                    logging.warning(f"Click+fill failed: {e2}, trying type")
                    # Método 3: Type character by character (más lento pero seguro)
                    textarea.click()
                    page.wait_for_timeout(300)
                    textarea.press("Control+A")
                    textarea.press("Backspace")
                    page.wait_for_timeout(300)
                    textarea.type(batch_text, delay=10)
                    logging.info(
                        f"Typed {len(tracking_numbers)} tracking numbers character by character"
                    )

            # Verificar que el contenido se haya ingresado
            page.wait_for_timeout(500)
            current_value = textarea.input_value()
            if not current_value or len(current_value) < 10:
                logging.error(
                    f"Textarea appears empty after filling! Current value length: {len(current_value) if current_value else 0}"
                )
                # Último intento: Focus + paste
                logging.debug("Last attempt: using clipboard paste...")
                textarea.focus()
                page.evaluate(
                    """(text) => {
                        const textarea = document.querySelector('textarea#auto-size-textarea');
                        if (textarea) {
                            textarea.focus();
                            textarea.value = text;
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }""",
                    batch_text
                )
                page.wait_for_timeout(500)
            else:
                logging.info(
                    f"Textarea content verified: {len(current_value)} characters")

            page.wait_for_timeout(1000)

            # Find and click Rastrear button - SELECTOR EXACTO
            logging.info("Looking for Rastrear button...")

            # Selector principal basado en el HTML exacto
            track_button = page.locator(
                'div.batch_track_search-area-bottom__MV_vI.btn-primary'
            )

            try:
                track_button.wait_for(state="visible", timeout=10000)
                logging.info("Rastrear button found!")

                # Scroll to button to ensure it's in viewport
                track_button.scroll_into_view_if_needed()
                page.wait_for_timeout(500)

            except Exception as e:
                logging.error(f"Primary button selector failed: {e}")
                # Try fallback
                fallback_buttons = [
                    'div.batch_track_search-area-bottom__MV_vI:has-text("Rastrear")',
                    'div.btn-primary:has-text("Rastrear")',
                    'div[class*="search-area-bottom"]:has-text("Rastrear")',
                    'div.cursor-pointer:has-text("Rastrear")',
                    'div.btn.btn-block:has-text("Rastrear")'
                ]
                for selector in fallback_buttons:
                    try:
                        track_button = page.locator(selector).first
                        track_button.wait_for(state="visible", timeout=5000)
                        logging.info(f"Button found with fallback: {selector}")
                        track_button.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        break
                    except:
                        continue
                else:
                    logging.warning("No button found, pressing Enter")
                    textarea.press("Enter")
                    page.wait_for_timeout(1000)
                    track_button = None

            if track_button:
                # Try clicking with force if needed
                try:
                    track_button.click()
                    logging.info("Clicked Rastrear button successfully")
                except Exception as e:
                    logging.warning(
                        f"Normal click failed, trying force click: {e}")
                    try:
                        track_button.click(force=True)
                        logging.info("Force clicked Rastrear button")
                    except Exception as e2:
                        logging.error(f"Force click also failed: {e2}")
                        # Final fallback: JavaScript click
                        track_button.evaluate("element => element.click()")
                        logging.info("JavaScript clicked Rastrear button")

            # Wait for results to load
            logging.info("Waiting for results to load...")
            page.wait_for_timeout(8000)

            # Extract all results
            results = self._extract_results_from_page(page)

            logging.info("Batch complete: %d results extracted", len(results))

            # Fill missing results with empty status
            result_dict = dict(results)
            complete_results = []
            for tn in tracking_numbers:
                status = result_dict.get(tn, "")
                complete_results.append((tn, status))

            return complete_results

        except Exception as e:
            logging.error("Error processing batch: %s", e)
            # Return empty results for all tracking numbers
            return [(tn, "") for tn in tracking_numbers]

        finally:
            with suppress(Exception):
                if page:
                    page.close()
            with suppress(Exception):
                if context:
                    context.close()

    def _extract_results_from_page(
        self,
        page
    ) -> List[Tuple[str, str]]:
        """
        Extract all tracking results from the page.
        Returns list of (tracking_id, status) tuples.
        """
        results: List[Tuple[str, str]] = []

        try:
            # Find all result containers
            result_divs = page.locator(
                'div.flex.items-center.gap-2:'
                'has(span.text-sm.font-medium.truncate)'
            )

            count = result_divs.count()
            logging.info("Found %d result divs", count)

            if count == 0:
                # Fallback: try broader selector
                logging.debug("Trying fallback selector...")
                result_divs = page.locator(
                    'div:has(span[title]):'
                    'has(div.text-sm.text-text-primary)'
                )
                count = result_divs.count()
                logging.info("Fallback found %d result divs", count)

            for i in range(count):
                try:
                    div = result_divs.nth(i)

                    # Extract tracking ID from title attribute or text
                    id_locator = div.locator(
                        'span.text-sm.font-medium.truncate'
                    )
                    tracking_id = id_locator.get_attribute('title')

                    if not tracking_id:
                        tracking_id = id_locator.inner_text()

                    tracking_id = tracking_id.strip()

                    # Extract status (without time)
                    status_locator = div.locator(
                        'div.text-sm.text-text-primary.'
                        'flex.items-center.gap-1'
                    )
                    status_text = status_locator.inner_text()
                    status_text = self._clean_status(status_text)

                    if tracking_id and status_text:
                        results.append((tracking_id, status_text))
                        logging.debug(
                            "Extracted: %s -> %s",
                            tracking_id,
                            status_text
                        )

                except Exception as e:
                    logging.warning("Error extracting result %d: %s", i, e)
                    continue

        except Exception as e:
            logging.error("Error extracting results: %s", e)

        return results

    def close(self):
        with suppress(Exception):
            if self.browser:
                self.browser.close()
        with suppress(Exception):
            if self._pw:
                self._pw.stop()
