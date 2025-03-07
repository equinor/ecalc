import abc

from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy.component_energy_context import ComponentEnergyContext
from libecalc.domain.energy.energy_model import EnergyModel


class Emitter(abc.ABC):
    """
    Something that emits something.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> dict[str, EmissionResult] | None: ...
