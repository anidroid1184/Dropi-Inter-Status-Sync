"""
Servicio de tracking refactorizado que delega responsabilidades.

Este servicio actúa como fachada para las operaciones de tracking,
delegando responsabilidades específicas a servicios especializados
y manteniendo compatibilidad hacia atrás con el código existente.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from typing import List, Dict, Any
import logging

from .status_normalizer import StatusNormalizer
from .alert_calculator import AlertCalculator, BusinessRules
from ..utils.constants import ColumnHeaders, StatusValues


class TrackerService:
    """
    Servicio principal de tracking que coordina operaciones especializadas.
    
    Actúa como fachada para las operaciones de tracking, delegando
    responsabilidades específicas a servicios especializados mientras
    mantiene una interfaz compatible con el código existente.
    
    Este servicio se enfoca en:
    - Coordinación entre servicios especializados
    - Preparación de datos para Google Sheets
    - Mantenimiento de compatibilidad hacia atrás
    """

    # ==================== MÉTODOS DE COMPATIBILIDAD HACIA ATRÁS ====================
    
    @staticmethod
    def normalize_status(raw_status: str) -> str:
        """
        Normaliza un estado raw delegando al StatusNormalizer.
        
        Mantiene compatibilidad hacia atrás con el código existente.
        
        Args:
            raw_status (str): Estado raw a normalizar
            
        Returns:
            str: Estado normalizado
        """
        return StatusNormalizer.normalize_status(raw_status)

    @staticmethod
    def explain_normalization(raw_status: str) -> Dict[str, str]:
        """
        Explica cómo se normalizó un estado delegando al StatusNormalizer.
        
        Mantiene compatibilidad hacia atrás con el código existente.
        
        Args:
            raw_status (str): Estado raw a analizar
            
        Returns:
            Dict: Información de la normalización
        """
        return StatusNormalizer.explain_normalization(raw_status)

    @staticmethod
    def compute_alert(dropi_status: str, tracking_status: str) -> str:
        """
        Calcula alertas delegando al AlertCalculator.
        
        Mantiene compatibilidad hacia atrás con el código existente.
        
        Args:
            dropi_status (str): Estado de Dropi
            tracking_status (str): Estado del tracking
            
        Returns:
            str: "TRUE" o "FALSE"
        """
        return AlertCalculator.compute_alert(dropi_status, tracking_status)

    @staticmethod
    def can_query(dropi_status: str) -> bool:
        """
        Determina si se puede consultar tracking delegando a BusinessRules.
        
        Mantiene compatibilidad hacia atrás con el código existente.
        
        Args:
            dropi_status (str): Estado de Dropi
            
        Returns:
            bool: True si se puede consultar
        """
        return BusinessRules.can_query_tracking(dropi_status)

    @staticmethod
    def terminal(dropi_status: str, tracking_status: str) -> bool:
        """
        Verifica estados terminales delegando a BusinessRules.
        
        Mantiene compatibilidad hacia atrás con el código existente.
        
        Args:
            dropi_status (str): Estado de Dropi
            tracking_status (str): Estado del tracking
            
        Returns:
            bool: True si algún estado es terminal
        """
        return BusinessRules.is_terminal_state(dropi_status, tracking_status)

    @staticmethod
    def prepare_new_rows(
        source_data: List[Dict[str, Any]], 
        existing_guias: set
    ) -> List[List[str]]:
        """
        Prepara filas nuevas para insertar en Google Sheets.
        
        Procesa datos fuente y crea filas para agregar a la hoja de tracking,
        excluyendo duplicados y validando datos requeridos.
        
        Args:
            source_data (List[Dict]): Datos fuente del archivo Excel
            existing_guias (set): Conjunto de GUIAs ya existentes
            
        Returns:
            List[List[str]]: Lista de filas para insertar en Sheets
        """
        new_rows = []
        processed_count = 0
        
        for item in source_data:
            # Extraer y validar número de guía
            guia = str(item.get(ColumnHeaders.ID_TRACKING, "")).strip()
            if not guia or len(guia) < 3:  # Validación básica
                continue
                
            # Evitar duplicados
            if guia in existing_guias:
                continue
            
            # Preparar fila con valores por defecto
            new_row = [
                str(item.get(ColumnHeaders.ID_DROPI, "")).strip(),
                guia,
                str(item.get(ColumnHeaders.STATUS_DROPI, "")).strip(),
                "",  # STATUS_TRACKING inicialmente vacío
                StatusValues.COINCIDE_FALSE,  # COINCIDEN por defecto FALSE
            ]
            
            new_rows.append(new_row)
            existing_guias.add(guia)
            processed_count += 1
        
        logging.info(f"Preparadas {processed_count} filas nuevas para insertar")
        return new_rows
