"""Status Normalizer para APP COMPARER (Coordinadora).

Normaliza estados de Coordinadora y Dropi para comparación.
"""
import os
import json
import logging
from typing import Dict, List


class StatusNormalizer:
    """Normaliza estados de Coordinadora y Dropi para comparar.

    - Carga coordinadora_map.json y dropi_map.json desde el directorio.
    - Para Coordinadora: busca variantes (coincidencia parcial, case-insensitive)
    - Para Dropi: mapea valores exactos (uppercase) usando dropi_map.json
    """

    def __init__(self):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        coord_path = os.path.join(app_dir, "coordinadora_map.json")
        dropi_path = os.path.join(app_dir, "dropi_map.json")

        self.coordinadora_map = self._load_map(coord_path)
        self.dropi_map = self._load_map(dropi_path)

        logging.info(f"Coordinadora map: {len(self.coordinadora_map)} keys")
        logging.info(f"Dropi map: {len(self.dropi_map)} entries")

    @staticmethod
    def _load_map(path: str) -> Dict[str, List[str]]:
        if not os.path.exists(path):
            logging.error(f"Map file not found: {path}")
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                return data
        except Exception as e:
            logging.exception(f"Error loading map {path}: {e}")
            return {}

    def normalize_coordinadora(self, raw_text: str) -> str:
        """Normaliza texto crudo de Coordinadora a palabra clave.

        Convenciones:
        - Lowercase matching, se permiten coincidencias parciales.
        - Retorna la clave tal cual (ej: 'ENTREGADO') o 'DESCONOCIDO'.
        """
        if not raw_text or not isinstance(raw_text, str):
            return "DESCONOCIDO"

        clean = raw_text.strip().lower()

        for key, variants in self.coordinadora_map.items():
            for variant in variants:
                if not isinstance(variant, str):
                    continue
                v = variant.strip().lower()
                if v in clean or clean in v:
                    logging.debug(
                        f"Coordinadora: '{raw_text}' -> '{key}' via '{variant}'"
                    )
                    return key

        logging.warning(f"Coordinadora: sin mapping para: '{raw_text}'")
        return "DESCONOCIDO"

    def normalize_dropi(self, status: str) -> str:
        """Normaliza estado Dropi usando dropi_map.json.

        - Usa upper() y busca en el diccionario de dropi_map (keys exactas).
        - Si no existe, convierte a formato UPPER_CASE_WITH_UNDERSCORES.
        """
        if not status or not isinstance(status, str):
            return "DESCONOCIDO"

        s = status.strip().upper()
        if s in self.dropi_map:
            return self.dropi_map[s]

        # Fallback: normalize whitespace to underscore
        candidate = s.replace(" ", "_")
        return candidate if candidate else "DESCONOCIDO"


# instancia global
_normalizer = StatusNormalizer()


def normalize_coordinadora(raw_text: str) -> str:
    return _normalizer.normalize_coordinadora(raw_text)


def normalize_dropi(status: str) -> str:
    return _normalizer.normalize_dropi(status)

