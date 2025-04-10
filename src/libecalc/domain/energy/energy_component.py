import abc

from libecalc.common.component_type import ComponentType
from libecalc.core.result import EcalcModelResult
from libecalc.domain.energy.component_energy_context import ComponentEnergyContext
from libecalc.domain.energy.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem, ProcessUnit


class EnergyComponent(abc.ABC):
    """
    A component in the energy model, aka a node in the energy graph. This might be a provider or consumer or both.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

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
    def is_container(self) -> bool:
        """
        Whether the energy component is a container for other energy components.
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

    @abc.abstractmethod
    def get_process_changed_events(self) -> list[ProcessChangedEvent]: ...

    @abc.abstractmethod
    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | ProcessUnit | None:
        """
        Get the process system that is active from the given event.
        Args:
            event: the process changed event we want a process system from

        Returns: a process system representing the process after the given event

        """
        ...


class EvaluatableEnergyComponent(EnergyComponent, abc.ABC):
    @abc.abstractmethod
    def evaluate_energy_usage(self, energy_context: ComponentEnergyContext) -> EcalcModelResult: ...
