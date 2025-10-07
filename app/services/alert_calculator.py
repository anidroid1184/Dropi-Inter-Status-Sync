"""
Servicio de lógica de alertas y reglas de negocio.

Este módulo contiene la lógica específica para calcular alertas entre estados
de Dropi e Interrapidísimo, así como reglas de negocio para determinar cuándo
realizar consultas web y detectar estados terminales.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from typing import Set
import logging

from ..utils.constants import StatusValues


class AlertCalculator:
    """
    Calculador de alertas basado en diferencias entre estados.

    Implementa las reglas de negocio para determinar cuándo generar
    alertas basadas en discrepancias entre el estado reportado por
    Dropi y el estado real del tracking en Interrapidísimo.
    """

    @staticmethod
    def compute_alert(dropi_status: str, tracking_status: str) -> str:
        """
        Calcula si debe generarse una alerta basada en los estados.

        Reglas de alerta implementadas:
        1. GUIA_GENERADA en Dropi pero ENTREGADO en web -> ALERTA
        2. ENTREGADO en Dropi pero diferente en web -> ALERTA  
        3. DEVOLUCION en Dropi pero diferente en web -> ALERTA
        4. Cualquier otra diferencia -> ALERTA
        5. Estados iguales -> SIN ALERTA

        Args:
            dropi_status (str): Estado normalizado de Dropi
            tracking_status (str): Estado normalizado del tracking web

        Returns:
            str: "TRUE" si requiere alerta, "FALSE" caso contrario

        Example:
            >>> AlertCalculator.compute_alert("GUIA_GENERADA", "ENTREGADO")
            'TRUE'
            >>> AlertCalculator.compute_alert("EN_TRANSITO", "EN_TRANSITO")
            'FALSE'
        """
        dropi = dropi_status or StatusValues.PENDIENTE
        tracking = tracking_status or StatusValues.PENDIENTE

        # Logging para auditoría
        logging.debug(
            f"Calculando alerta: Dropi='{dropi}' vs Tracking='{tracking}'")

        # Regla 1: Dropi dice GUIA_GENERADA pero web dice ENTREGADO
        if dropi == StatusValues.GUIA_GENERADA and tracking == StatusValues.ENTREGADO:
            logging.info(
                f"Alerta: Guía generada en Dropi pero entregado en web")
            return StatusValues.ALERT_TRUE

        # Regla 2: Dropi dice ENTREGADO pero web dice otra cosa
        if dropi == StatusValues.ENTREGADO and tracking != StatusValues.ENTREGADO:
            logging.info(
                f"Alerta: Entregado en Dropi pero '{tracking}' en web")
            return StatusValues.ALERT_TRUE

        # Regla 3: Dropi dice DEVOLUCION pero web dice otra cosa
        if dropi == StatusValues.DEVOLUCION and tracking != StatusValues.DEVOLUCION:
            logging.info(
                f"Alerta: Devolución en Dropi pero '{tracking}' en web")
            return StatusValues.ALERT_TRUE

        # Regla 4: Cualquier otra diferencia
        if dropi != tracking:
            logging.debug(
                f"Alerta: Estados diferentes - Dropi: '{dropi}', Web: '{tracking}'")
            return StatusValues.ALERT_TRUE

        # Regla 5: Estados iguales, no hay alerta
        logging.debug(f"Sin alerta: Estados coinciden - '{dropi}'")
        return StatusValues.ALERT_FALSE


class BusinessRules:
    """
    Reglas de negocio para el sistema de tracking.

    Contiene lógica para determinar cuándo realizar consultas web,
    identificar estados terminales y otras reglas del dominio.
    """

    @staticmethod
    def can_query_tracking(dropi_status: str) -> bool:
        """
        Determina si se debe consultar el tracking web para un estado Dropi.

        Solo consulta para estados no terminales y actionables que pueden
        tener actualizaciones útiles desde el sistema web.

        Args:
            dropi_status (str): Estado normalizado de Dropi

        Returns:
            bool: True si debe consultarse el tracking web

        Example:
            >>> BusinessRules.can_query_tracking("ENTREGADO")
            False
            >>> BusinessRules.can_query_tracking("EN_TRANSITO")
            True
        """
        status = dropi_status or StatusValues.PENDIENTE

        # Usar conjunto de estados consultables desde constantes
        queryable = status in StatusValues.QUERYABLE_STATES

        logging.debug(
            f"Estado '{status}' {'es' if queryable else 'no es'} consultable")
        return queryable

    @staticmethod
    def is_terminal_state(dropi_status: str, tracking_status: str) -> bool:
        """
        Determina si alguno de los estados representa un estado terminal.

        Estados terminales son aquellos donde el paquete ya no está en tránsito
        y no se esperan más actualizaciones significativas.

        Args:
            dropi_status (str): Estado normalizado de Dropi
            tracking_status (str): Estado normalizado del tracking web

        Returns:
            bool: True si algún estado es terminal

        Example:
            >>> BusinessRules.is_terminal_state("EN_TRANSITO", "ENTREGADO")
            True
            >>> BusinessRules.is_terminal_state("EN_TRANSITO", "EN_AGENCIA")
            False
        """
        dropi = dropi_status or StatusValues.PENDIENTE
        tracking = tracking_status or StatusValues.PENDIENTE

        terminal_found = (
            dropi in StatusValues.TERMINAL_STATES or
            tracking in StatusValues.TERMINAL_STATES
        )

        if terminal_found:
            logging.debug(
                f"Estado terminal detectado - Dropi: '{dropi}', Tracking: '{tracking}'")

        return terminal_found

    @staticmethod
    def should_update_frequently(dropi_status: str) -> bool:
        """
        Determina si un estado requiere actualizaciones frecuentes.

        Algunos estados como EN_TRANSITO o EN_REPARTO cambian rápidamente
        y se benefician de consultas más frecuentes.

        Args:
            dropi_status (str): Estado normalizado de Dropi

        Returns:
            bool: True si requiere actualizaciones frecuentes
        """
        high_frequency_states = {
            StatusValues.EN_TRANSITO,
            "EN_REPARTO",
            "EN_BODEGA_DESTINO",
            "INTENTO_DE_ENTREGA"
        }

        status = dropi_status or StatusValues.PENDIENTE
        return status in high_frequency_states

    @staticmethod
    def get_priority_level(dropi_status: str, tracking_status: str) -> int:
        """
        Calcula el nivel de prioridad para procesamiento.

        Returns:
            int: Nivel de prioridad (1=máxima, 5=mínima)
        """
        dropi = dropi_status or StatusValues.PENDIENTE
        tracking = tracking_status or StatusValues.PENDIENTE

        # Prioridad 1: Alertas críticas
        if AlertCalculator.compute_alert(dropi, tracking) == StatusValues.ALERT_TRUE:
            if dropi == StatusValues.ENTREGADO or tracking == StatusValues.ENTREGADO:
                return 1

        # Prioridad 2: Estados terminales recientes
        if BusinessRules.is_terminal_state(dropi, tracking):
            return 2

        # Prioridad 3: Estados de alta frecuencia
        if BusinessRules.should_update_frequently(dropi):
            return 3

        # Prioridad 4: Estados consultables normales
        if BusinessRules.can_query_tracking(dropi):
            return 4

        # Prioridad 5: Estados estables o no consultables
        return 5
