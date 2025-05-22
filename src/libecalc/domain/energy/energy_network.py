import abc
from dataclasses import dataclass
from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit


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


class PowerConsumer(abc.ABC):
    @abc.abstractmethod
    def get_power_consumption(self) -> TimeSeries: ...


class PowerProvider(abc.ABC):
    @abc.abstractmethod
    def get_power_demand(self) -> TimeSeries: ...


class FuelConsumer(abc.ABC):
    @abc.abstractmethod
    def get_fuel_consumption(self) -> TimeSeries: ...


class EnergyNetwork(abc.ABC):
    @abc.abstractmethod
    def get_energy_nodes(self) -> list[PowerConsumer | PowerProvider | FuelConsumer]: ...

    @abc.abstractmethod
    def get_power_providers(self) -> list[PowerProvider]: ...

    @abc.abstractmethod
    def get_power_consumers(self, energy_node_id: UUID) -> list[PowerConsumer]: ...


class EnergyModel(abc.ABC):
    @abc.abstractmethod
    def get_energy_networks(self) -> list[EnergyNetwork]: ...
