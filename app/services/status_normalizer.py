"""
Servicio de normalización de estados de tracking.

Este módulo se encarga exclusivamente de la normalización de estados de tracking
entre diferentes sistemas (Dropi, Interrapidísimo), aplicando reglas de mapeo,
overrides y heurísticas de forma consistente.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from typing import Dict
import json
import os
import logging

from ..utils.constants import StatusValues


class StatusNormalizer:
    """
    Normalizador de estados de tracking entre sistemas.

    Aplica reglas de normalización jerárquicas para convertir estados raw
    de diferentes sistemas a estados canónicos del sistema, con soporte
    para overrides, mapeos JSON y heurísticas de fallback.

    Attributes:
        NORM_MAP (Dict[str, str]): Mapeo heurístico de keywords a estados
        OVERRIDES (Dict[str, str]): Reglas de override con precedencia alta
        _compiled_map (Dict[str, str]): Mapeo compilado desde archivos JSON
    """

    # Mapeo heurístico de keywords a estados normalizados
    NORM_MAP = {
        "entregado": StatusValues.ENTREGADO,
        "transito": StatusValues.EN_TRANSITO,
        "tránsito": StatusValues.EN_TRANSITO,
        "camino": StatusValues.EN_TRANSITO,
        "ruta": StatusValues.EN_TRANSITO,
        "centro": StatusValues.EN_TRANSITO,
        "pendiente": StatusValues.PENDIENTE,
        "origen": StatusValues.PENDIENTE,
        "recibimos": StatusValues.EN_TRANSITO,
        "devuelto": StatusValues.DEVOLUCION,
        "devolución": StatusValues.DEVOLUCION,
        "retorno": StatusValues.DEVOLUCION,
        "agencia": StatusValues.EN_AGENCIA,
        "recoger": StatusValues.EN_AGENCIA,
        "guia_generada": StatusValues.GUIA_GENERADA,
        "guía generada": StatusValues.GUIA_GENERADA,
        "preparado_para_transportadora": StatusValues.GUIA_GENERADA,
        "preparado para transportadora": StatusValues.GUIA_GENERADA,
    }

    # Reglas de override con precedencia más alta que mapeos JSON
    OVERRIDES = {
        "envío pendiente por admitir": StatusValues.PENDIENTE,
        "envio pendiente por admitir": StatusValues.PENDIENTE,
        "pendiente por admitir": StatusValues.PENDIENTE,
    }

    _compiled_map: Dict[str, str] | None = None

    @classmethod
    def _load_json_mappings(cls) -> Dict[str, str]:
        """
        Carga y compila mapeos de keywords desde archivos JSON.

        Combina los mapeos de Dropi y Interrapidísimo en un diccionario
        único de keywords en minúsculas a estados normalizados.

        Returns:
            Dict[str, str]: Diccionario compilado de keyword -> estado

        Note:
            Los archivos JSON deben tener formato:
            {"ESTADO": ["keyword1", "keyword2", ...]}
        """
        if cls._compiled_map is not None:
            return cls._compiled_map

        base_dir = os.path.dirname(os.path.dirname(__file__))
        dropi_path = os.path.join(base_dir, "dropi_map.json")
        inter_path = os.path.join(base_dir, "interrapidisimo_traking_map.json")

        compiled: Dict[str, str] = {}

        def _ingest_mapping_file(path: str) -> None:
            """
            Ingiere un archivo de mapeo JSON específico.

            Args:
                path (str): Ruta al archivo JSON de mapeo
            """
            try:
                if not os.path.exists(path):
                    logging.warning(f"Archivo de mapeo no encontrado: {path}")
                    return

                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Formato esperado: { "STATUS": ["keyword1", "keyword2", ...] }
                for status, keywords in data.items():
                    if not isinstance(keywords, list):
                        continue

                    for keyword in keywords:
                        if isinstance(keyword, str) and keyword.strip():
                            compiled[keyword.strip().lower()
                                     ] = status.strip().upper()

                logging.info(f"Cargados {len(data)} mapeos desde {path}")

            except Exception as e:
                logging.warning(f"Error cargando mapeos desde {path}: {e}")

        # Cargar ambos archivos de mapeo
        _ingest_mapping_file(dropi_path)
        _ingest_mapping_file(inter_path)

        cls._compiled_map = compiled
        logging.info(f"Mapeos JSON compilados: {len(compiled)} keywords")
        return compiled

    @classmethod
    def _apply_alias_rules(cls, status: str) -> str:
        """
        Aplica reglas de alias para normalizar variaciones de estados.

        Args:
            status (str): Estado a normalizar

        Returns:
            str: Estado con aliases aplicados
        """
        # Normalizar DEVUELTO -> DEVOLUCION para consistencia
        if status == "DEVUELTO":
            return StatusValues.DEVOLUCION
        return status

    @classmethod
    def normalize_status(cls, raw_status: str) -> str:
        """
        Normaliza un estado raw a estado canónico del sistema.

        Aplica reglas de normalización en orden jerárquico:
        1. Estados vacíos -> PENDIENTE
        2. Overrides (precedencia alta)
        3. Mapeos JSON compilados
        4. Heurísticas de fallback
        5. Fallback final -> EN_TRANSITO

        Args:
            raw_status (str): Estado raw del sistema fuente

        Returns:
            str: Estado normalizado del sistema canónico

        Example:
            >>> StatusNormalizer.normalize_status("En tránsito hacia destino")
            'EN_TRANSITO'
            >>> StatusNormalizer.normalize_status("ENVÍO PENDIENTE POR ADMITIR")
            'PENDIENTE'
        """
        if not raw_status or not raw_status.strip():
            return StatusValues.PENDIENTE

        text = raw_status.strip().lower()

        # 1. Verificar overrides (precedencia más alta)
        for phrase, status in cls.OVERRIDES.items():
            if phrase in text:
                return cls._apply_alias_rules(status)

        # 2. Verificar mapeos JSON compilados
        compiled_mappings = cls._load_json_mappings()
        for keyword, status in compiled_mappings.items():
            if keyword in text:
                return cls._apply_alias_rules(status)

        # 3. Aplicar heurísticas de fallback
        for keyword, status in cls.NORM_MAP.items():
            if keyword in text:
                return cls._apply_alias_rules(status)

        # 4. Fallback seguro para estados no reconocidos
        logging.debug(
            f"Estado no reconocido, aplicando fallback: '{raw_status}'")
        return StatusValues.EN_TRANSITO

    @classmethod
    def explain_normalization(cls, raw_status: str) -> Dict[str, str]:
        """
        Explica cómo se normalizó un estado, útil para debugging y auditoría.

        Args:
            raw_status (str): Estado raw a analizar

        Returns:
            Dict con claves:
            - matched (bool): Si se encontró coincidencia
            - via (str): Método usado ('override'|'mapping'|'heuristic'|'fallback')
            - keyword (str|None): Keyword que coincidió (si aplica)
            - status (str): Estado normalizado resultante
            - raw (str): Estado original

        Example:
            >>> result = StatusNormalizer.explain_normalization("pendiente por admitir")
            >>> result['via']
            'override'
            >>> result['keyword']
            'pendiente por admitir'
        """
        raw = raw_status or ""

        if not raw.strip():
            return {
                "matched": False,
                "via": "fallback",
                "keyword": None,
                "status": StatusValues.PENDIENTE,
                "raw": raw
            }

        text = raw.strip().lower()

        # Verificar overrides
        for phrase, status in cls.OVERRIDES.items():
            if phrase in text:
                return {
                    "matched": True,
                    "via": "override",
                    "keyword": phrase,
                    "status": cls._apply_alias_rules(status),
                    "raw": raw
                }

        # Verificar mapeos JSON
        compiled_mappings = cls._load_json_mappings()
        for keyword, status in compiled_mappings.items():
            if keyword in text:
                return {
                    "matched": True,
                    "via": "mapping",
                    "keyword": keyword,
                    "status": cls._apply_alias_rules(status),
                    "raw": raw
                }

        # Verificar heurísticas
        for keyword, status in cls.NORM_MAP.items():
            if keyword in text:
                return {
                    "matched": True,
                    "via": "heuristic",
                    "keyword": keyword,
                    "status": cls._apply_alias_rules(status),
                    "raw": raw
                }

        # Fallback
        return {
            "matched": False,
            "via": "fallback",
            "keyword": None,
            "status": StatusValues.EN_TRANSITO,
            "raw": raw
        }

    @classmethod
    def reset_cache(cls) -> None:
        """
        Resetea la caché de mapeos compilados.

        Útil para testing o cuando los archivos de mapeo cambian
        durante la ejecución de la aplicación.
        """
        logging.debug("Reseteando caché de mapeos de normalización")
        cls._compiled_map = None
