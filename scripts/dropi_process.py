from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from typing import List

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from web.dropi_scraper_async import AsyncDropiScraper


def parse_trackings(arg: str | None) -> List[str]:
    if not arg:
        return []
    # allow comma separated values
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    return parts


def str2bool(v: str) -> bool:
    return str(v).lower() in {"1", "true", "yes", "y"}


async def run(args) -> int:
    setup_logging()
    logging.info("Starting Dropi (tercero) scraper in %s mode", "headless" if args.headless else "headful")

    scraper = AsyncDropiScraper(
        headless=args.headless,
        max_concurrency=args.max_concurrency,
        slow_mo=args.slow_mo,
        timeout_ms=args.timeout_ms,
        block_resources=args.block_resources,
    )
    await scraper.start()
    try:
        if not args.trackings:
            logging.error("Debes pasar al menos un tracking con --trackings (separado por coma)")
            return 2
        results = await scraper.get_status_many(
            args.trackings,
            url=args.url,
            search_selector=args.search_selector,
            status_selector=args.status_selector,
            expect_new_page=args.expect_new_page,
            rps=args.rps,
        )
        for tn, text in results:
            logging.info("%s => %s", tn, text)
        return 0
    finally:
        await scraper.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Dropi (tercero) scraping process - headful for inspection")
    parser.add_argument("--url", required=True, help="URL del portal del tercero")
    parser.add_argument("--search-selector", required=True, help="Selector del input de búsqueda (CSS/XPath/id)")
    parser.add_argument("--status-selector", default=None, help="Selector del elemento que contiene el estado (opcional)")
    parser.add_argument("--expect-new-page", type=str2bool, default=False, help="True si abre una nueva pestaña al consultar")

    parser.add_argument("--trackings", type=parse_trackings, default=[], help="Lista de guías separadas por coma")

    parser.add_argument("--headless", type=str2bool, default=False)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--rps", type=float, default=None)
    parser.add_argument("--slow-mo", dest="slow_mo", type=int, default=200)
    parser.add_argument("--timeout-ms", dest="timeout_ms", type=int, default=30000)
    parser.add_argument("--block-resources", type=str2bool, default=False)

    args = parser.parse_args()

    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        logging.warning("Interrumpido por el usuario")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
