import abc
from uuid import UUID


class Fuel(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...
