import abc
import datetime
from dataclasses import dataclass

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.domain.node import Node


@dataclass(frozen=True)
class TimeSeries:
    periods: list[Period]
    values: list[float]
    unit: Unit


class CalibratedTimeSeries(abc.ABC):
    @abc.abstractmethod
    def get_calibrated_value(self) -> TimeSeries: ...

    @abc.abstractmethod
    def get_original_value(self) -> TimeSeries: ...


class PowerConsumer(Node, abc.ABC):
    @abc.abstractmethod
    def get_power_demand(self) -> TimeSeries:
        """
        The required or requested amount of power by the consumer
        """
        ...


class PowerProvider(Node, abc.ABC):
    @abc.abstractmethod
    def get_power_output(self) -> TimeSeries:
        """
        The actual power delivered by a provider or component
        """
        ...

    @abc.abstractmethod
    def get_power_supply(self) -> TimeSeries | None:
        """
        The amount of power made available by the provider
        """
        ...


class FuelConsumer(Node, abc.ABC):
    @abc.abstractmethod
    def get_fuel_consumption(self) -> TimeSeries: ...


class EnergyNetwork(abc.ABC):
    @abc.abstractmethod
    def get_energy_nodes(self) -> list[PowerConsumer | PowerProvider | FuelConsumer]: ...


@dataclass(frozen=True)
class EnergyChangedEvent:
    """
    An event representing a change in the energy network
    """

    start: datetime
    name: str
    description: str | None = None
