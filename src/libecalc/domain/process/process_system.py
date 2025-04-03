import abc
from uuid import UUID

from libecalc.domain.process.core.stream.stream import Stream


class ProcessUnit(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_type(self) -> str: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...


class ProcessSystem(abc.ABC):
    @abc.abstractmethod
    def get_process_units(self) -> list[ProcessUnit]: ...

    @abc.abstractmethod
    def get_streams(self) -> list[Stream]: ...
