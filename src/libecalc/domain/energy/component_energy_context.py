import abc
from typing import Optional

from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate


class ComponentEnergyContext(abc.ABC):
    """
    The context for which a component should be calculated.
    """

    @abc.abstractmethod
    def get_power_requirement(self) -> Optional[TimeSeriesFloat]:
        """
        Get power demand for the component.
        Returns:

        """

    @abc.abstractmethod
    def get_fuel_usage(self) -> Optional[TimeSeriesStreamDayRate]:
        """
        Get fuel usage for the component.
        Returns:
        """
