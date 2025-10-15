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
            # Create new context
            if self._headless:
                context = self.browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
            else:
                context = self.browser.new_context(viewport=None)
                
            page = context.new_page()
            
            # Navigate to 17track Envía page
            url = "https://www.17track.net/es/carriers/env%C3%ADa-envia"
            logging.info(
                "Processing batch of %d tracking numbers",
                len(tracking_numbers)
            )
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            
            # Wait for page to load
            page.wait_for_timeout(2000)

            # Try to accept cookie banners
            with suppress(Exception):
                cookie_btn = page.locator(
                    'button:has-text("Aceptar")'
                ).first
                cookie_btn.click(timeout=2000)
                logging.debug("Cookie banner clicked")

            # Find the textarea
            textarea = page.locator(
                '#auto-size-textarea.batch_track_textarea__rhhSa'
            )
            textarea.wait_for(state="visible", timeout=15000)
            textarea.scroll_into_view_if_needed()

            # Fill with tracking numbers (max 40, one per line)
            batch_text = "\n".join(tracking_numbers[:40])
            textarea.fill(batch_text)
            logging.debug("Filled %d tracking numbers", len(tracking_numbers))

            # Find and click the search/track button
            track_button = page.locator(
                'button:has-text("Rastrear"), button:has-text("Track")'
            ).first
            track_button.click()
            logging.debug("Clicked track button")

            # Wait for results to load
            page.wait_for_timeout(5000)  # Give time for all results

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
