from __future__ import annotations
from typing import List, Dict
import json
import os


class TrackerService:
    """Business rules for status normalization, alerts, and decisions."""

    NORM_MAP = {
        "entregado": "ENTREGADO",
        "transito": "EN_TRANSITO",
        "tránsito": "EN_TRANSITO",
        "camino": "EN_TRANSITO",
        "ruta": "EN_TRANSITO",
        "centro": "EN_TRANSITO",
        "pendiente": "PENDIENTE",
        "origen": "PENDIENTE",
        "recibimos": "EN_TRANSITO",
        "devuelto": "DEVUELTO",
        "devolución": "DEVUELTO",
        "retorno": "DEVUELTO",
        "agencia": "EN_AGENCIA",
        "recoger": "EN_AGENCIA",
        "guia_generada": "GUIA_GENERADA",
        "guía generada": "GUIA_GENERADA",
        "preparado_para_transportadora": "GUIA_GENERADA",
        "preparado para transportadora": "GUIA_GENERADA",
    }

    # Override rules to maintain expected behavior from tests/business
    # Example: The phrase "ENVÍO PENDIENTE POR ADMITIR" should normalize to PENDIENTE
    OVERRIDES = {
        "envío pendiente por admitir": "PENDIENTE",
        "envio pendiente por admitir": "PENDIENTE",
        "pendiente por admitir": "PENDIENTE",
    }

    _COMPILED_MAP: Dict[str, str] | None = None

    @staticmethod
    def _load_mappings() -> Dict[str, str]:
        """Load and compile keyword->status mapping from JSON files once.

        It merges both Dropi and Inter mappings into a single lowercase keyword
        dictionary. Later, OVERRIDES and NORM_MAP provide precedence/fallbacks.
        """
        if TrackerService._COMPILED_MAP is not None:
            return TrackerService._COMPILED_MAP

        base_dir = os.path.dirname(os.path.dirname(__file__))  # project root
        dropi_path = os.path.join(base_dir, "dropi_map.json")
        inter_path = os.path.join(base_dir, "interrapidisimo_traking_map.json")

        compiled: Dict[str, str] = {}

        def _ingest(path: str):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # data format: { "STATUS": ["keyword1", "keyword2", ...] }
                for status, keywords in data.items():
                    for kw in keywords:
                        if isinstance(kw, str):
                            compiled[kw.strip().lower()] = status.strip().upper()
            except Exception:
                # If the file doesn't exist or is invalid, skip silently to keep runtime resilient
                pass

        _ingest(dropi_path)
        _ingest(inter_path)

        TrackerService._COMPILED_MAP = compiled
        return compiled

    @staticmethod
    def normalize_status(s: str) -> str:
        if not s:
            return "PENDIENTE"
        text = s.strip().lower()

        # 1) Overrides have highest precedence
        for phrase, status in TrackerService.OVERRIDES.items():
            if phrase in text:
                return status

        # 2) JSON compiled mappings from Dropi + Inter
        compiled = TrackerService._load_mappings()
        for kw, status in compiled.items():
            if kw in text:
                return status

        # 3) Legacy heuristics fallback to keep behavior backwards compatible
        for k, v in TrackerService.NORM_MAP.items():
            if k in text:
                return v

        return "EN_TRANSITO"  # safe fallback

    @staticmethod
    def explain_normalization(s: str) -> dict:
        """Explain how a raw status string was normalized.

        Returns a dict with keys:
        - matched: bool
        - via: one of 'override' | 'mapping' | 'heuristic' | 'fallback'
        - keyword: the matched keyword/phrase (if any)
        - status: the normalized status result
        - raw: original string
        """
        raw = s or ""
        if not raw:
            return {"matched": False, "via": "fallback", "keyword": None, "status": "PENDIENTE", "raw": raw}

        text = raw.strip().lower()

        # Overrides
        for phrase, status in TrackerService.OVERRIDES.items():
            if phrase in text:
                return {"matched": True, "via": "override", "keyword": phrase, "status": status, "raw": raw}

        # JSON compiled mappings
        compiled = TrackerService._load_mappings()
        for kw, status in compiled.items():
            if kw in text:
                return {"matched": True, "via": "mapping", "keyword": kw, "status": status, "raw": raw}

        # Heuristic map
        for k, v in TrackerService.NORM_MAP.items():
            if k in text:
                return {"matched": True, "via": "heuristic", "keyword": k, "status": v, "raw": raw}

        # Fallback
        return {"matched": False, "via": "fallback", "keyword": None, "status": "EN_TRANSITO", "raw": raw}

    @staticmethod
    def compute_alert(dropi: str, tracking: str) -> str:
        d, w = dropi, tracking
        if d == "GUIA_GENERADA" and w == "ENTREGADO":
            return "TRUE"
        if d == "ENTREGADO" and w != "ENTREGADO":
            return "TRUE"
        if d == "DEVUELTO" and w != "DEVUELTO":
            return "TRUE"
        if d != w:
            return "TRUE"
        return "FALSE"

    @staticmethod
    def can_query(dropi: str) -> bool:
        # Allow querying for all non-terminal, actionable states
        return dropi in {
            "GUIA_GENERADA",
            "PENDIENTE",
            "EN_PROCESAMIENTO",
            "EN_BODEGA_TRANSPORTADORA",
            "EN_TRANSITO",
            "EN_BODEGA_DESTINO",
            "EN_REPARTO",
            "INTENTO_DE_ENTREGA",
            "NOVEDAD",
            "REEXPEDICION",
            "REENVIO",
            "EN_AGENCIA",
        }

    @staticmethod
    def terminal(dropi: str, tracking: str) -> bool:
        return ("ENTREGADO" in {dropi, tracking}) or ("DEVUELTO" in {dropi, tracking})

    @staticmethod
    def prepare_new_rows(source_data: List[Dict], existing_guias: set) -> List[List[str]]:
        rows = []
        for item in source_data:
            guia = item.get("ID TRACKING", "").strip()
            if not guia or guia in existing_guias:
                continue
            rows.append([
                item.get("ID DROPI", ""),
                guia,
                item.get("STATUS DROPI", ""),
                "",
                "FALSE",
            ])
            existing_guias.add(guia)
        return rows
