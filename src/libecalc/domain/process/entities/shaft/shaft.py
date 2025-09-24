from abc import ABC, abstractmethod


class Shaft(ABC):
    """Abstract base class for a shaft.

    Can be expanded to include more properties and methods as needed.
    Name, id, units connected to it, etc
    """

    def __init__(self, speed_rpm: float | None = None):
        self._speed_rpm = speed_rpm

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
    def set_speed(self, value: float):
        if self._speed_rpm is None:
            self._speed_rpm = value
        elif value != self._speed_rpm:
            raise AttributeError("Speed has already been set. Cannot modify speed of SingleSpeedShaft")


class VariableSpeedShaft(Shaft):
    def set_speed(self, value: float):
        self._speed_rpm = value
