"""Comparer app para Coordinadora.

Lee la hoja de cálculo, normaliza estados y escribe la columna COINCIDEN.
Además escribe un reporte simple en una hoja llamada REPORTE_COORDINADORA.
"""

import logging
import argparse
from typing import List, Dict

from comparer_config import load_settings
from comparer_credentials import load_service_account_credentials
from comparer_sheets import SheetsClient
import comparer_normalizer as normalizer


def run(dry_run: bool = False) -> None:
    settings = load_settings()

    creds = load_service_account_credentials(settings.credentials_path)
    if creds is None:
        logging.error("No se pudieron cargar credenciales. Salida.")
        return

    client = SheetsClient(creds, settings.spreadsheet_name)

    # Asegurar columna COINCIDEN
    client.ensure_columns(["COINCIDEN"])

    records = client.read_all_records()

    updates: List[tuple] = []
    total = 0
    matches = 0
    no_matches = 0
    unknown_transport = 0

    for idx, rec in enumerate(records, start=2):
        total += 1

        # soportar nombres con/ sin underscore
        status_dropi = rec.get("STATUS DROPI") or rec.get("STATUS_DROPI") or rec.get("STATUS_DROP")
        status_trans = rec.get("STATUS TRANSPORTADORA") or rec.get("STATUS_TRANSPORTADORA") or rec.get("STATUS_TRANSPORT")

        dropi_norm = normalizer.normalize_dropi(status_dropi)
        trans_norm = normalizer.normalize_coordinadora((status_trans or "").lower())

        if trans_norm == "DESCONOCIDO":
            result = "DESCONOCIDO"
            unknown_transport += 1
        else:
            result = "SI" if dropi_norm == trans_norm else "NO"
            if result == "SI":
                matches += 1
            else:
                no_matches += 1

        updates.append((idx, {"COINCIDEN": result}))

    logging.info(f"Total: {total}  SI: {matches}  NO: {no_matches}  DESCONOCIDO: {unknown_transport}")

    if dry_run:
        logging.info("Dry run: no se escribirán cambios")
        return

    # Ejecutar batch update
    client.batch_update_comparison(updates)
    logging.info("Comparación completada")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Comparer Coordinadora -> Dropi")
    parser.add_argument("--dry-run", action="store_true", help="No escribe cambios")

    args = parser.parse_args()

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

