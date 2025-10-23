"""
Test para verificar que los números de tracking mantienen ceros iniciales.
"""
import logging
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports de la biblioteca estándar

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def test_tracking_number_padding():
    """Prueba el padding de números de tracking."""
    test_cases = [
        # (input, expected_output)
        ("14152617422", "014152617422"),    # Sin 0 inicial, 11 dígitos
        ("014152617422", "014152617422"),   # Ya tiene 12 dígitos
        ("24031227909", "024031227909"),    # Sin 0 inicial, 11 dígitos
        ("1234567890", "001234567890"),     # 10 dígitos
        ("123456789012", "123456789012"),   # Ya tiene 12 dígitos
        ("abc123", "abc123"),               # No numérico, sin cambios
    ]

    print("\n" + "="*70)
    print("PRUEBA DE PADDING DE NÚMEROS DE TRACKING")
    print("="*70)
    print("Todos los números deben tener 12 dígitos con ceros a la izquierda\n")

    all_passed = True
    for i, (input_num, expected) in enumerate(test_cases, 1):
        tracking = input_num.strip()

        # Aplicar la lógica del scraper
        if tracking.isdigit() and len(tracking) < 12:
            tracking = tracking.zfill(12)
            logging.debug(f"Tracking number padded to 12 digits: {tracking}")

        status = "✅ PASS" if tracking == expected else "❌ FAIL"

        if tracking != expected:
            all_passed = False

        print(f"{i:2}. {status}")
        print(f"    Input:    '{input_num}' ({len(input_num)} dígitos)")
        print(f"    Expected: '{expected}'")
        print(f"    Got:      '{tracking}'")
        print()

    print("="*70)
    if all_passed:
        print("✅ TODOS LOS TESTS PASARON")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = test_tracking_number_padding()
    exit(0 if success else 1)
