import abc
from typing import Optional

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult


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
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]: ...
