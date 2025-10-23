"""
Test unitario para verificar el formato de números de tracking.
"""
from scraper_web_async import AsyncEnviaScraper
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports del proyecto


def test_format_tracking_number():
    """Prueba la función de formateo de números de tracking."""
    scraper = AsyncEnviaScraper()

    test_cases = [
        # (input, expected_output)
        ("014152617422", "014-152617422"),  # ¡Preserva el 0 inicial!
        ("014152357292", "014-152357292"),
        ("014152336849", "014-152336849"),
        ("024031227909", "024-031227909"),
        ("014152252243", "014-152252243"),
        ("14152617422", "141-52617422"),    # Sin 0 inicial
        ("123456789012", "123-456789012"),
        ("1234567890", "123-4567890"),
        ("1234", "123-4"),
        ("123", "123"),  # Muy corto, sin cambios
        ("12", "12"),    # Muy corto, sin cambios
        # Con guiones o espacios existentes
        ("014-152617422", "014-152617422"),  # Ya formateado
        ("014 152 617 422", "014-152617422"),  # Con espacios
        ("014-152-617-422", "014-152617422"),  # Con múltiples guiones
    ]

    print("\n" + "="*70)
    print("PRUEBA DE FORMATO DE NÚMEROS DE TRACKING")
    print("="*70)
    print(f"Formato esperado: XXX-XXXXXXXXXX (3 dígitos, guion, resto)\n")

    all_passed = True
    for i, (input_num, expected) in enumerate(test_cases, 1):
        result = scraper._format_tracking_number(input_num)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result != expected:
            all_passed = False

        print(f"{i:2}. {status}")
        print(f"    Input:    '{input_num}'")
        print(f"    Expected: '{expected}'")
        print(f"    Got:      '{result}'")
        print()

    print("="*70)
    if all_passed:
        print("✅ TODOS LOS TESTS PASARON")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = test_format_tracking_number()
    exit(0 if success else 1)
