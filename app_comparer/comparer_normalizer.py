"""
Status Normalizer para APP COMPARER.

Normaliza estados de Interrapidísimo (texto crudo de la web) a palabras clave
para comparación con STATUS DROPI.

Responsabilidades:
- Normalizar STATUS INTERRAPIDISIMO (texto crudo) usando mapeo JSON
- Buscar coincidencias parciales en el texto crudo
- Retornar palabra clave correspondiente para comparación

Flujo:
1. Recibe texto crudo: "Tu envío fue entregado"
2. Busca en inter_map.json: {"ENTREGADO": ["tu envío fue entregado", ...]}
3. Retorna palabra clave: "ENTREGADO"

Autor: Sistema de Tracking Dropi-Inter
Fecha: Enero 2025
Versión: 2.0.0
"""

from __future__ import annotations
import os
import json
import logging
from typing import Dict, List


class StatusNormalizer:
    """
    Normalizador de estados para comparación.
    
    Usa inter_map.json con formato:
    {
      "PALABRA_CLAVE": ["variante1", "variante2", ...]
    }
    
    Attributes:
        inter_map: Mapeo palabra_clave → lista de variantes
    """
    
    def __init__(self):
        """Inicializa el normalizador cargando inter_map.json."""
        app_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(app_dir, "inter_map.json")
        
        self.inter_map = self._load_inter_map(map_path)
        logging.info(f"Mapa cargado con {len(self.inter_map)} palabras clave")
    
    @staticmethod
    def _load_inter_map(path: str) -> Dict[str, List[str]]:
        """
        Carga mapeo desde inter_map.json.
        
        Args:
            path: Ruta al archivo JSON
            
        Returns:
            Dict[str, List[str]]: Mapeo palabra_clave → [variantes]
        """
        if not os.path.exists(path):
            logging.error(f"Archivo de mapeo no encontrado: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"Mapa cargado exitosamente desde {path}")
                return data
        except Exception as e:
            logging.error(f"Error cargando mapeo {path}: {e}")
            return {}
    
    def normalize_interrapidisimo(self, raw_text: str) -> str:
        """
        Normaliza texto crudo de Interrapidísimo a palabra clave.
        
        Busca coincidencias parciales en el texto crudo usando el mapa.
        
        Args:
            raw_text: Texto crudo de la web (ej: "Tu envío fue entregado")
            
        Returns:
            str: Palabra clave (ej: "ENTREGADO") o "DESCONOCIDO"
            
        Examples:
            >>> normalize_interrapidisimo("Tu envío fue entregado")
            "ENTREGADO"
            >>> normalize_interrapidisimo("en tránsito")
            "EN_TRANSITO"
        """
        if not raw_text or not isinstance(raw_text, str):
            return "DESCONOCIDO"
        
        # Limpiar y convertir a minúsculas para comparación
        clean_text = raw_text.strip().lower()
        
        # Buscar coincidencia en cada palabra clave
        for keyword, variants in self.inter_map.items():
            for variant in variants:
                variant_lower = variant.lower()
                
                # Buscar coincidencia exacta o parcial
                if variant_lower in clean_text or clean_text in variant_lower:
                    logging.debug(f"Match: '{clean_text}' → '{keyword}' (via '{variant}')")
                    return keyword
        
        # No se encontró coincidencia
        logging.warning(f"No se encontró mapeo para: '{raw_text}'")
        return "DESCONOCIDO"
    
    def normalize_dropi(self, status: str) -> str:
        """
        Normaliza estado de Dropi (generalmente ya viene normalizado).
        
        Args:
            status: Estado de Dropi
            
        Returns:
            str: Estado normalizado
        """
        if not status or not isinstance(status, str):
            return "DESCONOCIDO"
        
        # Dropi generalmente ya viene normalizado, solo limpiar
        clean = status.strip().upper().replace(" ", "_")
        return clean if clean else "DESCONOCIDO"
    
    @classmethod
    def normalize(cls, raw_text: str, source: str = "inter") -> str:
        """
        Método de clase para normalizar estados (API simplificada).
        
        Args:
            raw_text: Texto a normalizar
            source: Fuente ("inter" para Interrapidísimo, "dropi" para Dropi)
            
        Returns:
            str: Estado normalizado
        """
        if source == "inter":
            return _normalizer.normalize_interrapidisimo(raw_text)
        else:
            return _normalizer.normalize_dropi(raw_text)


# Instancia global
_normalizer = StatusNormalizer()
