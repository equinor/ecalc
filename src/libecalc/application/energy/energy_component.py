import abc

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.model_change_event import ModelChangeEvent
from libecalc.common.component_type import ComponentType
from libecalc.core.result import EcalcModelResult


class EnergyComponent(abc.ABC):
    """
    A component in the energy model, aka a node in the energy graph. This might be a provider or consumer or both.

    TODO: might also be an emitter, which consumes or provides no energy.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def get_component_process_type(self) -> ComponentType: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def get_change_events(self) -> list[ModelChangeEvent]:
        """
        Get all the change events for this component
        """
        ...

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


class EvaluatableEnergyComponent(EnergyComponent, abc.ABC):
    @abc.abstractmethod
    def evaluate_energy_usage(self, energy_context: ComponentEnergyContext) -> EcalcModelResult: ...
