import numpy as np
from numpy._typing import NDArray

from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.interfaces.power_loss_factor_interface import PowerLossFactorInterface
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import ExpressionType


class PowerLossFactor(PowerLossFactorInterface):
    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        expression: ExpressionType | None = None,
    ):
        self._expression = convert_expression(expression)
        self._expression_evaluator = expression_evaluator

    def as_vector(self) -> NDArray[np.float64] | None:
        """Evaluate power loss factor expression and compute resulting power loss factor vector.

        Args:
            expression_evaluator (ExpressionEvaluator): Service with all info to evaluate expressions.
            power_loss_factor_expression: The condition expression

        Returns:
            Assembled power loss factor vector
        """
        if self._expression is None:
            return None

        power_loss_factor = self._expression_evaluator.evaluate(expression=self._expression)
        return np.array(power_loss_factor)

    def apply_to_array(
        self,
        energy_usage: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Apply resulting required power taking a (cable/motor...) power loss factor into account.

        Args:
            energy_usage: initial required energy usage [MW]
            power_loss_factor: Optional factor of the power (cable) loss.

        Returns:
            energy usage where power loss is accounted for, i.e. energy_usage/(1-power_loss_factor)
        """
        power_loss_factor = self.as_vector()
        if power_loss_factor is None:
            return energy_usage.copy()
        else:
            return energy_usage / (1.0 - power_loss_factor)
