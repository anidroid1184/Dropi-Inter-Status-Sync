"""
Alert Calculator para APP COMPARER.

Calcula si debe activarse una alerta según reglas de negocio.

Responsabilidades:
- Evaluar si estados no coinciden
- Detectar estados terminales (ENTREGADO, DEVUELTO)
- Aplicar reglas de negocio para alertas

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import logging
from typing import Set


# Estados terminales que no deben tener discrepancias
TERMINAL_STATES: Set[str] = {
    "ENTREGADO",
    "DEVUELTO",
    "CANCELADO"
}


class AlertCalculator:
    """
    Calculador de alertas según reglas de negocio.
    """
    
    @staticmethod
    def is_terminal(status: str) -> bool:
        """
        Verifica si un estado es terminal.
        
        Args:
            status: Estado normalizado
            
        Returns:
            bool: True si es estado terminal
        """
        return status in TERMINAL_STATES
    
    @staticmethod
    def compute_alert(dropi_status: str, web_status: str) -> str:
        """
        Calcula si debe haber alerta.
        
        Reglas:
        1. Si coinciden -> no alerta
        2. Si alguno es terminal y no coinciden -> ALERTA
        3. Si ninguno es terminal -> no alerta (aún en tránsito)
        
        Args:
            dropi_status: Estado normalizado de Dropi
            web_status: Estado normalizado de Web
            
        Returns:
            str: "TRUE" o "FALSE"
        """
        # Sin estados válidos
        if not dropi_status or not web_status:
            return "FALSE"
        
        # Si coinciden, no hay alerta
        if dropi_status == web_status:
            return "FALSE"
        
        # Si alguno es terminal y no coinciden, hay alerta
        if AlertCalculator.is_terminal(dropi_status) or AlertCalculator.is_terminal(web_status):
            logging.debug(
                f"ALERTA: {dropi_status} vs {web_status} "
                f"(alguno es terminal)"
            )
            return "TRUE"
        
        # Ambos en tránsito, no alerta
        return "FALSE"


# Funciones helper para compatibilidad
def is_terminal(status: str) -> bool:
    """
    Verifica si un estado es terminal.
    
    Args:
        status: Estado normalizado
        
    Returns:
        bool: True si es estado terminal
    """
    return AlertCalculator.is_terminal(status)


def compute_alert(dropi_status: str, web_status: str) -> str:
    """
    Calcula si debe haber alerta.
    
    Reglas:
    1. Si coinciden -> no alerta
    2. Si alguno es terminal y no coinciden -> ALERTA
    3. Si ninguno es terminal -> no alerta (aún en tránsito)
    
    Args:
        dropi_status: Estado normalizado de Dropi
        web_status: Estado normalizado de Web
        
    Returns:
        str: "TRUE" o "FALSE"
    """
    return AlertCalculator.compute_alert(dropi_status, web_status)
