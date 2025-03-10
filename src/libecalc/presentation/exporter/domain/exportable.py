from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit


class ExportableType(str, Enum):
    INSTALLATION = "INSTALLATION"


class ConsumptionType(str, Enum):
    FUEL = "FUEL"
    ELECTRICITY = "ELECTRICITY"


@dataclass
class AttributeMeta:
    fuel_category: str | None
    consumer_category: str | None
    producer_category: str | None = None
    emission_type: str | None = None


class Attribute(ABC):
    @abstractmethod
    def datapoints(self) -> Iterable[tuple[Period, float]]: ...

    @abstractmethod
    def get_meta(self) -> AttributeMeta: ...


@dataclass
class AttributeSet(ABC):
    attributes: list[Attribute]

    def __iter__(self) -> Iterator[Attribute]:
        return self.attributes.__iter__()


class Exportable(ABC):
    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_category(self) -> str: ...

    @abstractmethod
    def get_periods(self) -> Periods: ...

    @abstractmethod
    def get_fuel_consumption(self) -> AttributeSet: ...

    @abstractmethod
    def get_power_consumption(self, unit: Unit) -> AttributeSet: ...

    @abstractmethod
    def get_emissions(self, unit: Unit) -> AttributeSet: ...

    @abstractmethod
    def get_electricity_production(self, unit: Unit) -> AttributeSet: ...

    @abstractmethod
    def get_maximum_electricity_production(self, unit: Unit) -> AttributeSet: ...

    @abstractmethod
    def get_storage_volumes(self, unit: Unit) -> AttributeSet: ...


class ExportableSet(ABC):
    @abstractmethod
    def get_from_type(self, exportable_type: ExportableType) -> list[Exportable]: ...
