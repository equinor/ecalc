from __future__ import annotations

from libecalc.domain.process.entities.process_units.exceptions import ProcessUnitException


class ChokeValveException(ProcessUnitException):
    """Base exception for choke valve operations."""

    pass


class NegativePressureDropException(ChokeValveException):
    """Exception raised when pressure drop is negative."""

    def __init__(self, delta_p_bar: float):
        self.delta_p_bar = delta_p_bar
        super().__init__(
            f"Pressure drop cannot be negative: {delta_p_bar:.2f} bar. "
            "Use a positive value to reduce outlet pressure."
        )


class InvalidPressureDropException(ChokeValveException):
    """Exception raised when pressure drop would result in negative outlet pressure."""

    def __init__(self, inlet_pressure: float, delta_p_bar: float):
        self.inlet_pressure = inlet_pressure
        self.delta_p_bar = delta_p_bar
        outlet_pressure = inlet_pressure - delta_p_bar
        super().__init__(
            f"Invalid pressure drop: inlet pressure {inlet_pressure:.2f} bara - "
            f"pressure drop {delta_p_bar:.2f} bar = {outlet_pressure:.2f} bara (negative pressure not allowed)"
        )


class ChokeValveNotCalculatedException(ChokeValveException):
    """Exception raised when trying to access calculation results before calculation."""

    def __init__(self):
        super().__init__("ChokeValve has not been calculated yet. Call calculate() first.")
