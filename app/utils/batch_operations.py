"""
Módulo de operaciones batch para Google Sheets.

Este módulo proporciona utilidades optimizadas para realizar actualizaciones
masivas en Google Sheets, minimizando las llamadas API y respetando los 
límites de cuota del servicio.

Autor: Sistema de Tracking Dropi-Inter  
Fecha: Octubre 2025
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import logging

from ..services.sheets_client import SheetsClient


class BatchOperations:
    """
    Operaciones batch optimizadas para Google Sheets.

    Esta clase proporciona métodos eficientes para realizar actualizaciones
    masivas en hojas de cálculo, agrupando cambios por columnas y rangos
    consecutivos para minimizar las llamadas API.

    Attributes:
        CHUNK_SIZE (int): Tamaño máximo de chunk para respetarlos límites API
    """

    CHUNK_SIZE = 100  # Máximo rangos por request según límites Google API

    @staticmethod
    def flush_batch_updates(
        sheets: SheetsClient,
        batch_updates: List[Tuple[int, List[Any]]]
    ) -> None:
        """
        Escribe solo las celdas exactas que cambiaron en la hoja de cálculo.

        Agrupa las actualizaciones por índice de columna y luego las divide
        en bloques de filas consecutivas, actualizando cada bloque por separado.
        Esto evita limpiar celdas en filas que no forman parte del batch.

        Args:
            sheets (SheetsClient): Cliente configurado para la hoja destino
            batch_updates (List[Tuple[int, List[Any]]]): Lista de tuplas donde
                cada tupla contiene (número_fila, [valores_por_columna])

        Raises:
            Exception: Si hay errores en la comunicación con Google Sheets API

        Example:
            >>> updates = [(2, ["valor1", None, "valor3"]), (3, [None, "valor2"])]
            >>> BatchOperations.flush_batch_updates(sheets_client, updates)
        """
        if not batch_updates:
            logging.debug("No hay actualizaciones batch para procesar")
            return

        logging.info(f"Procesando {len(batch_updates)} actualizaciones batch")

        # Construir mapeo: col_idx -> list[(row, value)]
        by_col: Dict[int, List[Tuple[int, Any]]] = {}

        for row, arr in batch_updates:
            for col_idx, val in enumerate(arr, start=1):
                if val is None:
                    continue
                by_col.setdefault(col_idx, []).append((row, val))

        # Preparar payload batch agrupado por columnas y rangos consecutivos
        batched_payload: List[Dict[str, Any]] = []

        for col_idx, items in by_col.items():
            items.sort(key=lambda x: x[0])  # Ordenar por fila

            # Agrupar en bloques de filas consecutivas
            current_block: List[Tuple[int, Any]] = []
            prev_row = None

            def _flush_current_block():
                """Helper interno para procesar el bloque actual."""
                if not current_block:
                    return

                start_row = current_block[0][0]
                end_row = current_block[-1][0]
                values = [[value] for _, value in current_block]

                # Convertir índice de columna a letra (A, B, C, etc.)
                col_letter = chr(ord('A') + col_idx - 1)
                range_a1 = f"{col_letter}{start_row}:{col_letter}{end_row}"

                batched_payload.append({
                    "range": range_a1,
                    "values": values
                })

                logging.debug(
                    f"Agregado rango {range_a1} con {len(values)} valores"
                )

            # Procesar cada item y agrupar consecutivos
            for row, value in items:
                if prev_row is None or row == prev_row + 1:
                    current_block.append((row, value))
                else:
                    _flush_current_block()
                    current_block = [(row, value)]
                prev_row = row

            # Procesar último bloque
            _flush_current_block()

        # Enviar en chunks para respetar límites API
        if batched_payload:
            total_ranges = len(batched_payload)
            logging.info(f"Enviando {total_ranges} rangos en chunks de "
                         f"{BatchOperations.CHUNK_SIZE}")

            for i in range(0, total_ranges, BatchOperations.CHUNK_SIZE):
                chunk = batched_payload[i:i + BatchOperations.CHUNK_SIZE]

                try:
                    sheets.values_batch_update(chunk)
                    logging.debug(f"Chunk {i//BatchOperations.CHUNK_SIZE + 1} "
                                  f"enviado exitosamente ({len(chunk)} rangos)")

                except Exception as e:
                    logging.error(f"Error enviando chunk {i}: {str(e)}")
                    raise

        logging.info("Actualizaciones batch completadas exitosamente")


# Función de compatibilidad hacia atrás
def _flush_batch(
    sheets: SheetsClient,
    batch_updates: List[Tuple[int, List[Any]]]
) -> None:
    """
    Función de compatibilidad hacia atrás para código existente.

    Args:
        sheets: Cliente de Google Sheets
        batch_updates: Lista de actualizaciones batch

    Deprecated:
        Usar BatchOperations.flush_batch_updates() directamente
    """
    BatchOperations.flush_batch_updates(sheets, batch_updates)
