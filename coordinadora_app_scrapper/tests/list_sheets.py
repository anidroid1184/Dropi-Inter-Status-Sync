"""
Script para listar todas las hojas de Google Sheets disponibles.
Útil para verificar el nombre exacto de la hoja a usar.
"""
from scraper_credentials import load_credentials
import gspread
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports de terceros

# Imports del proyecto


# Cargar credenciales
credentials = load_credentials()
gc = gspread.authorize(credentials)

print("\n" + "="*60)
print("HOJAS DE GOOGLE SHEETS DISPONIBLES")
print("="*60 + "\n")

try:
    sheets = gc.openall()
    if not sheets:
        print("❌ No se encontraron hojas de cálculo.")
    else:
        for i, sheet in enumerate(sheets, 1):
            print(f"{i}. Nombre: {sheet.title}")
            print(f"   ID: {sheet.id}")
            print(f"   URL: {sheet.url}")
            print()
except Exception as e:
    print(f"❌ Error listando hojas: {e}")

print("="*60)
print("\nCopia el NOMBRE EXACTO o el ID de la hoja que quieres usar")
print("y actualízalo en el archivo .env como SPREADSHEET_NAME")
print("="*60 + "\n")
