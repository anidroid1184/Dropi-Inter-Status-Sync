"""
Script de prueba para el normalizador de estados.

Prueba la normalización de estados de Interrapidísimo usando el mapa.
"""

from comparer_normalizer import StatusNormalizer

def test_normalizer():
    """Prueba el normalizador con ejemplos reales."""
    
    # Casos de prueba basados en tu imagen
    test_cases = [
        ("Tu envío fue entregado", "ENTREGADO"),
        ("Tú envío fue entregado", "ENTREGADO"),
        ("Tu envio Fue devuelto", "REENVIO"),  # Según el mapa
        ("en tránsito", "EN_TRANSITO"),
        ("entregado", "ENTREGADO"),
        ("devuelto", "DEVUELTO"),
    ]
    
    normalizer = StatusNormalizer()
    
    print("=" * 70)
    print("PRUEBA DEL NORMALIZADOR DE INTERRAPIDÍSIMO")
    print("=" * 70)
    
    for raw_text, expected in test_cases:
        result = normalizer.normalize_interrapidisimo(raw_text)
        status = "✓" if result == expected else "✗"
        
        print(f"\n{status} Texto: '{raw_text}'")
        print(f"  → Resultado: {result}")
        print(f"  → Esperado:  {expected}")
    
    print("\n" + "=" * 70)
    
    # Probar algunos estados de Dropi
    print("\nPRUEBA DE NORMALIZACIÓN DROPI")
    print("=" * 70)
    
    dropi_cases = [
        "ENTREGADO",
        "EN_TRANSITO",
        "DEVUELTO",
        "NOVEDAD"
    ]
    
    for status in dropi_cases:
        result = normalizer.normalize_dropi(status)
        print(f"  '{status}' → '{result}'")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_normalizer()
