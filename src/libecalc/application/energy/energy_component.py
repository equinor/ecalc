import abc

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
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
    def evaluate_energy_usage(self, energy_context: ComponentEnergyContext) -> EcalcModelResult: ...
