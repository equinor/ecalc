from __future__ import annotations


class ChokeValveException(Exception):
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


class InvalidChokeValveParametersException(ChokeValveException):
    """Exception raised when choke valve parameters are invalid."""

    def __init__(self, message: str):
        super().__init__(f"Invalid choke valve parameters: {message}")


class NoInletStreamException(ChokeValveException):
    """Exception raised when trying to access inlet stream that hasn't been set."""

    def __init__(self):
        super().__init__("No inlet stream has been set for this choke valve")


class ChokeValveNotCalculatedException(ChokeValveException):
    """Exception raised when trying to access calculation results before calculation."""

    def __init__(self):
        super().__init__("ChokeValve has not been calculated yet. Call calculate() first.")


class NoInletStreamForCalculationException(ChokeValveException):
    """Exception raised when trying to calculate without an inlet stream."""

    def __init__(self):
        super().__init__("No inlet stream available for calculation. Set inlet stream first.")
