import abc
from uuid import UUID

from libecalc.common.component_type import ComponentType


class EnergyComponent(abc.ABC):
    """
    A component in the energy model, aka a node in the energy graph. This might be a provider or consumer or both.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_component_process_type(self) -> ComponentType: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def is_provider(self) -> bool:
        """
        Whether the energy component provides energy to other energy components.
        """
        ...

    @abc.abstractmethod
    def is_fuel_consumer(self) -> bool:
        """Returns True if the component consumes fuel"""
        ...

    @abc.abstractmethod
    def is_electricity_consumer(self) -> bool:
        """Returns True if the component consumes electricity"""
        ...
