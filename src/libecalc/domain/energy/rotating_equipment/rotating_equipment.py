from abc import ABC, abstractmethod


class RotatingEquipment(ABC):
    """A piece of rotating equipment that draws mechanical power from a shaft."""

    @abstractmethod
    def get_shaft_power_demand_mw(self) -> float:
        """Power drawn from the shaft [MW]."""
        ...
