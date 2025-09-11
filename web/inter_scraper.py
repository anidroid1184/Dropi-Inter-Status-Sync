from __future__ import annotations
import logging
from contextlib import suppress
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class InterScraper:
    """Playwright-based scraper to fetch tracking status from Interrapidísimo.

    This implementation keeps a single browser process alive and creates a new
    context per query to avoid state leakage. It returns the RAW status text
    found in the popup when possible; normalization is handled elsewhere by
    `TrackerService.normalize_status` using JSON mappings.
    """

    def __init__(self, headless: bool = True):
        self._pw = sync_playwright().start()
        self._headless = headless
        logging.info("Launching Playwright Chromium. headless=%s", headless)
        # Chromium tends to be the most stable target for Playwright
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        # Maximize and slow down actions when headful to observe behavior
        slow_mo = 250 if not headless else 0
        if not headless:
            launch_args.append("--start-maximized")
        self.browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=launch_args,
        )

    def get_status(self, tracking_number: str) -> str:
        """Return RAW status text found in popup (normalization is external).

        Fallbacks to an empty string when nothing is found so that the caller
        can decide normalization defaults.
        """
        context = None
        page = None
        popup = None
        try:
            # In headful mode, let the OS/window manage size (viewport=None)
            if getattr(self, "_headless", True):
                context = self.browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                context = self.browser.new_context(viewport=None)
            page = context.new_page()
            page.goto("https://interrapidisimo.com/sigue-tu-envio/", timeout=45000, wait_until="domcontentloaded")

            # Accept cookie banners if any to avoid blocking the input
            with suppress(Exception):
                page.get_by_role("button", name=lambda n: n and ("acept" in n.lower() or "de acuerdo" in n.lower() or "entendido" in n.lower())).click(timeout=2000)

            # Prefer the visible input among desktop/mobile selectors
            # The user confirmed mobile input: <input class="buscarGuiaInput" id="inputGuideMovil" ...>
            input_css = "#inputGuide:visible, #inputGuideMovil:visible, input.buscarGuiaInput:visible"
            try:
                loc = page.locator(input_css).first
                loc.wait_for(state="visible", timeout=15000)
                loc.scroll_into_view_if_needed()
            except PlaywrightTimeoutError:
                logging.error("Visible tracking input not found for %s", tracking_number)
                return ""

            # Some sites with type=number inputs behave better with fill than type
            with suppress(Exception):
                loc.fill("")
            loc.fill(tracking_number)

            # Follow the new tab that contains the detail status (context.expect_page is robust)
            try:
                with context.expect_page(timeout=20000) as new_page_info:
                    loc.press("Enter")
                popup = new_page_info.value
                with suppress(Exception):
                    popup.bring_to_front()
            except PlaywrightTimeoutError:
                # Fallback: no new page; continue in same page
                popup = None
                with suppress(PlaywrightTimeoutError):
                    page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Determine target (new tab or same page)
            # Note: Interrapidísimo suele abrir una nueva pestaña

            target = popup if popup is not None else page

            # Wait for content to render a bit
            with suppress(PlaywrightTimeoutError):
                target.wait_for_load_state("domcontentloaded", timeout=15000)

            status_text: str | None = None

            # Strict extraction: find the content card for current status and read the bold line
            try:
                # Anchor by the title 'Estado actual de tu envío' near the content card
                title = target.locator("css=div.content p.title-current-state").first
                title.wait_for(state="visible", timeout=15000)
                value = title.locator("xpath=following-sibling::p[contains(@class,'font-weight-600')][1]")
                value.wait_for(state="visible", timeout=15000)
                txt = value.inner_text().strip()
                if txt:
                    status_text = txt
            except PlaywrightTimeoutError:
                # As a backup, try a direct CSS to the value inside the content card
                with suppress(Exception):
                    value2 = target.locator("css=div.content p.font-weight-600").first
                    value2.wait_for(state="visible", timeout=5000)
                    txt2 = value2.inner_text().strip()
                    if txt2:
                        status_text = txt2

            # Fallback: only if content card text not found, use 'Sin novedad' badge
            if not status_text:
                with suppress(Exception):
                    novelty = target.locator("css=p.guide-WhitOut-Novelty").first
                    novelty.wait_for(state="visible", timeout=3000)
                    txt = novelty.inner_text().strip()
                    if txt:
                        status_text = txt

            return status_text or ""
        except Exception as e:
            logging.error("Scraper error for %s: %s", tracking_number, e)
            return ""
        finally:
            with suppress(Exception):
                if popup:
                    popup.close()
            with suppress(Exception):
                if page:
                    page.close()
            with suppress(Exception):
                if context:
                    context.close()

    def close(self):
        with suppress(Exception):
            if self.browser:
                self.browser.close()
        with suppress(Exception):
            if self._pw:
                self._pw.stop()
