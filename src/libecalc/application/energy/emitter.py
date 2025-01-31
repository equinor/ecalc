import abc
from typing import Optional

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.core.result.emission import EmissionResult


class Emitter(abc.ABC):
    """
    Something that emits something..
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def evaluate_emissions(
        self,
        energy_context: Optional[ComponentEnergyContext] = None,
        energy_model: Optional[EnergyModel] = None,
    ) -> Optional[dict[str, EmissionResult]]: ...
