import abc
from typing import TypeVar

from libecalc.common.utils.rates import TimeSeriesStreamDayRate, TimeSeriesVolumes
from libecalc.domain.common.entity import Entity
from libecalc.domain.common.entity_id import ID

ID_T = TypeVar("ID_T", bound=ID)


class StorageContainer(abc.ABC, Entity):
    @abc.abstractmethod
    def get_storage_volumes(self) -> TimeSeriesVolumes: ...

    @abc.abstractmethod
    def get_storage_rates(self) -> TimeSeriesStreamDayRate: ...
