from abc import ABC, abstractmethod


class Shaft(ABC):
    """Abstract base class for a shaft.

    A shaft is a physical rotating component that connects the driver (turbine/motor)
    to a compressor. The shaft owns mechanical efficiency, which accounts for
    losses in bearings, gearbox, and couplings.

    Attributes:
        mechanical_efficiency: Fraction of shaft power that becomes gas power.
            Constraint: 0 < η_mech ≤ 1. Default is 1.0 (no losses).
        speed_rpm: The rotational speed of the shaft in RPM.
    """

    def __init__(self, mechanical_efficiency: float = 1.0, speed_rpm: float | None = None):
        if not (0 < mechanical_efficiency <= 1):
            raise ValueError(f"Mechanical efficiency must be in the range (0, 1], got {mechanical_efficiency}")
        self._mechanical_efficiency = mechanical_efficiency
        self._speed_rpm = speed_rpm

    @property
    def mechanical_efficiency(self) -> float:
        """Fraction of shaft power that becomes gas power (0 < η ≤ 1)."""
        return self._mechanical_efficiency

    @abstractmethod
    def set_speed(self, value: float) -> None:
        pass

    def get_speed(self) -> float:
        if self._speed_rpm is None:
            return float("nan")
        return self._speed_rpm

    def reset_speed(self):
        self._speed_rpm = None

    @property
    def speed_is_defined(self) -> bool:
        return self._speed_rpm is not None


class SingleSpeedShaft(Shaft):
    """Shaft with fixed rotational speed. Once set, speed cannot be changed."""

    def set_speed(self, value: float):
        if self._speed_rpm is None:
            self._speed_rpm = value
        elif value != self._speed_rpm:
            raise AttributeError("Speed has already been set. Cannot modify speed of SingleSpeedShaft")


class VariableSpeedShaft(Shaft):
    """Shaft with variable rotational speed. Speed can be changed at runtime."""

    def set_speed(self, value: float):
        self._speed_rpm = value
