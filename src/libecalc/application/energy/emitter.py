import abc
from typing import Optional

from pydantic import Field

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult


class Emitter(abc.ABC):
    """
    Something that emits something.
    """

    expression_evaluator: Optional[ExpressionEvaluator] = Field(default=None, exclude=True)

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> Optional[dict[str, EmissionResult]]: ...

    def set_expression_evaluator(self, expression_evaluator: ExpressionEvaluator):
        self.expression_evaluator = expression_evaluator
