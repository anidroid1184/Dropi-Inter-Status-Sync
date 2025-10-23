"""
Script de prueba visual para debugging del scraper de Envía.
Ejecuta el scraper con modo NO headless para ver qué está pasando.
"""
from scraper_web_async import AsyncEnviaScraper
import logging
import asyncio
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports de la biblioteca estándar

# Imports del proyecto


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def test_visual():
    # IDs de tracking de prueba (usa tus propios IDs)
    test_tracking = [
        "14152626978",
        "14152627016",
        "14152627038"
    ]

    print("\n" + "="*60)
    print("PRUEBA VISUAL DEL SCRAPER ENVÍA")
    print("="*60)
    print(f"\nProcesando {len(test_tracking)} guías de prueba...")
    print("El navegador se abrirá en modo visible.")
    print("Observa el proceso para identificar problemas.\n")

    # Crear scraper en modo NO headless para ver qué pasa
    scraper = AsyncEnviaScraper(
        headless=False,  # Modo visible
        max_concurrency=1,
        slow_mo=500,  # Ralentizar para ver mejor
        timeout_ms=60000,  # 60 segundos de timeout
        batch_size=40
    )

    try:
        await scraper.start()

        print("Navegador iniciado. Procesando...")
        results = await scraper.get_status_many(test_tracking)

        print("\n" + "="*60)
        print("RESULTADOS:")
        print("="*60)
        for tracking_id, status in results:
            print(f"  {tracking_id}: {status or '[SIN RESULTADO]'}")
        print("="*60 + "\n")

    finally:
        input("\nPresiona Enter para cerrar el navegador...")
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_visual())
