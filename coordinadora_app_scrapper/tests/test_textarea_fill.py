"""
Script de prueba visual para verificar el ingreso de códigos en el textarea.
Ejecuta el scraper con headless=False para ver el navegador.
"""
from scraper_web_async import AsyncEnviaScraper
from scraper_logging import setup_logging
import logging
import asyncio
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports de la biblioteca estándar

# Imports del proyecto


async def test_textarea_fill():
    """Prueba visual del llenado del textarea."""
    setup_logging()
    logging.info("=== PRUEBA VISUAL DE TEXTAREA ===")

    # Códigos de prueba (sin formato, el scraper los formateará)
    test_codes = [
        "014152617422",
        "014152617423",
        "014152617424",
        "014152617425",
        "014152617426"
    ]

    logging.info(f"Códigos de prueba (originales): {test_codes}")
    logging.info(
        "El scraper los formateará como: XXX-XXXXXXXXXX "
        "(preservando ceros iniciales)"
    )

    # Crear scraper en modo NO headless para ver el navegador
    scraper = AsyncEnviaScraper(
        headless=False,  # ← Importante: ver el navegador
        max_concurrency=1,
        batch_size=40,
        slow_mo=500  # Ralentizar para ver mejor
    )

    try:
        await scraper.start()
        logging.info("Scraper iniciado. Procesando batch...")

        results = await scraper.get_status_batch(test_codes)

        logging.info("=== RESULTADOS ===")
        for tracking_id, status in results:
            logging.info(f"  {tracking_id}: {status or 'VACÍO'}")

        logging.info("=== PRUEBA COMPLETADA ===")
        logging.info(
            "Revisa visualmente si los códigos se ingresaron correctamente")

        # Mantener el navegador abierto por 10 segundos
        await asyncio.sleep(10)

    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_textarea_fill())
