"""
Script de prueba para el scraper de Coordinadora.

Prueba con una o varias guías reales.
"""

from scraper_coordinadora import obtener_estado


def probar_guia(guia: str):
    """Prueba una guía individual."""
    print(f"\n🔍 Probando guía: {guia}")
    print("-" * 50)

    estado = obtener_estado(guia)

    if estado:
        print(f"✅ Estado: {estado}")
    else:
        print("❌ No se pudo obtener el estado")

    return estado


def main():
    """Función principal de prueba."""
    print("="*50)
    print("PRUEBA DE SCRAPER COORDINADORA")
    print("="*50)

    # Guías de prueba
    guias_prueba = [
        "36394323151",  # La guía del ejemplo que diste
        # Agrega más guías aquí para probar
    ]

    resultados = {}

    for guia in guias_prueba:
        estado = probar_guia(guia)
        resultados[guia] = estado

    # Resumen
    print("\n" + "="*50)
    print("RESUMEN DE RESULTADOS")
    print("="*50)

    exitosas = sum(1 for e in resultados.values() if e)
    total = len(resultados)

    for guia, estado in resultados.items():
        simbolo = "✅" if estado else "❌"
        print(f"{simbolo} {guia}: {estado or 'ERROR'}")

    print(f"\nTotal: {exitosas}/{total} exitosas")
    print("="*50)


if __name__ == "__main__":
    main()
