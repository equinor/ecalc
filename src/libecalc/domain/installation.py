import abc
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.domain.energy import Emitter
from libecalc.domain.fuel import Fuel


class ElectricityProducer(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...
    @abc.abstractmethod
    def get_power_production(self) -> TimeSeriesRate: ...

    @abc.abstractmethod
    def get_maximum_power_production(self) -> TimeSeriesRate | None: ...


class StorageContainer(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_storage_rates(self) -> TimeSeriesRate: ...


@dataclass
class FuelConsumption:
    rate: TimeSeriesRate
    fuel: TemporalModel[Fuel]


class FuelConsumer(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_fuel(self) -> TemporalModel[Fuel]: ...

    @abc.abstractmethod
    def get_fuel_consumption(self) -> FuelConsumption: ...


class PowerConsumer(Protocol):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    def get_producer_id(self) -> UUID | None:
        """
        Producer does not always exist
        """
        ...

    def get_power_consumption(self) -> TimeSeriesRate: ...


class Installation(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def get_electricity_producers(self) -> list[ElectricityProducer]: ...

    @abc.abstractmethod
    def get_storage_containers(self) -> list[StorageContainer]: ...

    @abc.abstractmethod
    def get_fuel_consumers(self) -> list[FuelConsumer]: ...

    @abc.abstractmethod
    def get_power_consumers(self) -> list[PowerConsumer]:
        """
        Power consumers includes both electricity consumers and mechanical power consumers
        """
        ...

    @abc.abstractmethod
    def get_emitters(self) -> list[Emitter]: ...
