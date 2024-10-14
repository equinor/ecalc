from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, Iterator, List, Optional, Tuple

from libecalc.common.units import Unit


class ExportableType(str, Enum):
    INSTALLATION = "INSTALLATION"


class ConsumptionType(str, Enum):
    FUEL = "FUEL"
    ELECTRICITY = "ELECTRICITY"


@dataclass
class AttributeMeta:
    fuel_category: Optional[str]
    consumer_category: Optional[str]
    producer_category: Optional[str] = None
    emission_type: Optional[str] = None


class Attribute(ABC):
    @abstractmethod
    def datapoints(self) -> Iterable[Tuple[datetime, float]]: ...

    @abstractmethod
    def get_meta(self) -> AttributeMeta: ...


@dataclass
class AttributeSet(ABC):
    attributes: List[Attribute]

    def __iter__(self) -> Iterator[Attribute]:
        return self.attributes.__iter__()


class Exportable(ABC):
    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_category(self) -> str: ...

    @abstractmethod
    def get_timesteps(self) -> List[datetime]: ...

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
    def get_from_type(self, exportable_type: ExportableType) -> List[Exportable]: ...
