"""
Status Normalizer para APP COMPARER.

Normaliza estados de Dropi e Interrapidísimo a valores estándar.

Responsabilidades:
- Normalizar estados raw a valores comparables
- Aplicar mapeos desde archivos JSON
- Fallback a heurísticas si no hay mapeo

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
import json
import logging
from typing import Dict


class StatusNormalizer:
    """
    Normalizador de estados para comparación.
    
    Attributes:
        dropi_map: Mapeo de estados Dropi
        inter_map: Mapeo de estados Interrapidísimo
    """
    
    def __init__(self):
        """Inicializa el normalizador con mapeos desde JSON."""
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Cargar mapeos
        self.dropi_map = self._load_json(
            os.path.join(app_dir, "dropi_map.json")
        )
        self.inter_map = self._load_json(
            os.path.join(app_dir, "inter_map.json")
        )
    
    @staticmethod
    def _load_json(path: str) -> Dict[str, str]:
        """
        Carga mapeo desde archivo JSON.
        
        Args:
            path: Ruta al archivo JSON
            
        Returns:
            Dict: Mapeo cargado o vacío si no existe
        """
        if not os.path.exists(path):
            logging.warning(f"Archivo de mapeo no encontrado: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando mapeo {path}: {e}")
            return {}
    
    def normalize_status(
        self,
        raw_status: str,
        source: str = "dropi"
    ) -> str:
        """
        Normaliza un estado raw a valor estándar.
        
        Args:
            raw_status: Estado raw a normalizar
            source: Fuente del estado ("dropi" o "inter")
            
        Returns:
            str: Estado normalizado
        """
        if not raw_status or not isinstance(raw_status, str):
            return "PENDIENTE"
        
        # Limpiar
        clean = raw_status.strip().upper()
        
        # Aplicar mapeo
        mapping = self.dropi_map if source == "dropi" else self.inter_map
        
        if clean in mapping:
            return mapping[clean]
        
        # Heurísticas
        return self._apply_heuristics(clean)
    
    @staticmethod
    def _apply_heuristics(status: str) -> str:
        """
        Aplica heurísticas para normalización sin mapeo.
        
        Args:
            status: Estado limpio en mayúsculas
            
        Returns:
            str: Estado normalizado
        """
        # Detectar estados comunes
        if "ENTREGADO" in status or "ENTREGA" in status:
            return "ENTREGADO"
        
        if "DEVUELTO" in status or "DEVOLUCION" in status:
            return "DEVUELTO"
        
        if "TRANSITO" in status or "TRÁNSITO" in status:
            return "EN_TRANSITO"
        
        if "RECOLECCION" in status or "RECOLECCIÓN" in status:
            return "RECOLECTADO"
        
        if "NOVEDAD" in status:
            return "NOVEDAD"
        
        if "CANCELADO" in status:
            return "CANCELADO"
        
        # Default
        return "PENDIENTE"
    
    @classmethod
    def normalize(cls, raw_status: str, source: str = "dropi") -> str:
        """
        Método de clase para normalizar estados (API simplificada).
        
        Args:
            raw_status: Estado raw a normalizar
            source: Fuente del estado ("dropi" o "inter")
            
        Returns:
            str: Estado normalizado
        """
        return _normalizer.normalize_status(raw_status, source)


# Instancia global
_normalizer = StatusNormalizer()


def normalize_status(raw_status: str, source: str = "dropi") -> str:
    """
    Función helper para normalizar estados.
    
    Args:
        raw_status: Estado raw
        source: Fuente ("dropi" o "inter")
        
    Returns:
        str: Estado normalizado
    """
    return _normalizer.normalize_status(raw_status, source)
