import numpy as np

from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.condition import Condition
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_power_loss_factor,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.regularity import Regularity
from libecalc.expression import Expression


class PumpConsumerFunction(ConsumerFunction):
    """
    The pump consumer function defining the energy usage.

    Args:
        pump_function: The pump model
        rate_expression: Rate expression [Sm3/h]
        suction_pressure_expression: Suction pressure expression [bara]
        discharge_pressure_expression: Discharge pressure expression [bara]
        fluid_density_expression: Fluid density expression [kg/m3]
        condition_expression: Optional condition expression
        power_loss_factor_expression: Optional power loss factor expression.
            Typically used for power line loss subsea et.c.
    """

    def __init__(
        self,
        pump_function: PumpModel,
        rate_expression: Expression,
        suction_pressure_expression: Expression,
        discharge_pressure_expression: Expression,
        fluid_density_expression: Expression,
        condition: Condition,
        regularity: Regularity,
        power_loss_factor_expression: Expression = None,
    ):
        self.condition = condition
        self.regularity = regularity
        self._pump_function = pump_function
        self._rate_expression = rate_expression
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._fluid_density_expression = fluid_density_expression

        # Typically used for power line loss subsea et.c.
        self._power_loss_factor_expression = power_loss_factor_expression

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
    ) -> ConsumerFunctionResult:
        """Evaluate the pump consumer function

        Args:
            variables_map: Variables map is the VariablesMap-object holding all the data to be evaluated.
            regularity: The regularity of the pump consumer function (same as for installation pump is part of)

        Returns:
            Pump consumer function result
        """
        calendar_day_rate = expression_evaluator.evaluate(expression=self._rate_expression)

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        stream_day_rate = self.condition.apply_to_array(
            input_array=Rates.to_stream_day(
                calendar_day_rates=calendar_day_rate,
                regularity=self.regularity.get_values,
            )
        )

        suction_pressure = expression_evaluator.evaluate(expression=self._suction_pressure_expression)
        discharge_pressure = expression_evaluator.evaluate(expression=self._discharge_pressure_expression)
        fluid_density = expression_evaluator.evaluate(expression=self._fluid_density_expression)

        # Do not input regularity to pump function. Handled outside
        energy_function_result = self._pump_function.evaluate_rate_ps_pd_density(
            rate=stream_day_rate,
            suction_pressures=suction_pressure,
            discharge_pressures=discharge_pressure,
            fluid_density=fluid_density,
        )

        power_loss_factor = get_power_loss_factor_from_expression(
            expression_evaluator=expression_evaluator,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        pump_consumer_function_result = ConsumerFunctionResult(
            periods=expression_evaluator.get_periods(),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage),
            condition=self.condition.as_vector(),
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=np.asarray(energy_function_result.energy_usage),
                power_loss_factor=power_loss_factor,
            ),
        )
        return pump_consumer_function_result
