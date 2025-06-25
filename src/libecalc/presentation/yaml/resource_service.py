import abc
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.file_context import FileContext


@dataclass
class InvalidResource:
    message: str
    file_context: FileContext | None
    resource_name: str


TData = TypeVar("TData")
TupleWithError = tuple[TData, Sequence[InvalidResource]]


class ResourceService(abc.ABC):
    """
    A service to get a resource
    """

    @abc.abstractmethod
    def get_time_series_resources(self) -> TupleWithError[dict[str, TimeSeriesResource]]: ...

    @abc.abstractmethod
    def get_facility_resources(self) -> TupleWithError[dict[str, Resource]]: ...
