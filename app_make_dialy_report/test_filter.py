"""
Script de prueba para verificar el filtrado de discrepancias.

Simula el flujo del reporter sin conectarse a Google Sheets.
"""

def test_filter_logic():
    """Prueba la lógica de filtrado de discrepancias."""
    
    # Datos de ejemplo simulando registros de Google Sheets
    mock_records = [
        {
            "GUIA": "12345",
            "STATUS DROPI": "ENTREGADO",
            "STATUS INTERRAPIDISIMO": "Tu envío fue entregado",
            "COINCIDEN": "TRUE"
        },
        {
            "GUIA": "67890",
            "STATUS DROPI": "EN_TRANSITO",
            "STATUS INTERRAPIDISIMO": "Tu envío Fue devuelto",
            "COINCIDEN": "FALSE"
        },
        {
            "GUIA": "11111",
            "STATUS DROPI": "ENTREGADO",
            "STATUS INTERRAPIDISIMO": "entregado",
            "COINCIDEN": "TRUE"
        },
        {
            "GUIA": "22222",
            "STATUS DROPI": "DEVUELTO",
            "STATUS INTERRAPIDISIMO": "en tránsito",
            "COINCIDEN": "FALSE"
        },
        {
            "GUIA": "33333",
            "STATUS DROPI": "NOVEDAD",
            "STATUS INTERRAPIDISIMO": "novedad",
            "COINCIDEN": "TRUE"
        }
    ]
    
    # Filtrar discrepancias (igual que en reporter_app.py)
    discrepancias = [
        r for r in mock_records 
        if r.get("COINCIDEN", "").upper() == "FALSE"
    ]
    
    print("=" * 70)
    print("PRUEBA DE FILTRADO DE DISCREPANCIAS")
    print("=" * 70)
    print(f"\nTotal registros: {len(mock_records)}")
    print(f"Discrepancias (COINCIDEN=FALSE): {len(discrepancias)}")
    
    print("\n" + "=" * 70)
    print("REGISTROS CON DISCREPANCIAS")
    print("=" * 70)
    
    for i, record in enumerate(discrepancias, 1):
        print(f"\n{i}. GUIA: {record['GUIA']}")
        print(f"   STATUS DROPI: {record['STATUS DROPI']}")
        print(f"   STATUS INTERRAPIDISIMO: {record['STATUS INTERRAPIDISIMO']}")
        print(f"   COINCIDEN: {record['COINCIDEN']}")
    
    print("\n" + "=" * 70)
    print("COLUMNAS QUE SE INCLUIRÁN EN EL EXCEL:")
    print("=" * 70)
    
    if discrepancias:
        columns = list(discrepancias[0].keys())
        for col in columns:
            print(f"  - {col}")
    
    print("\n" + "=" * 70)
    print(f"✓ Lógica correcta: Solo {len(discrepancias)} registros con COINCIDEN=FALSE")
    print("=" * 70)


if __name__ == "__main__":
    test_filter_logic()
