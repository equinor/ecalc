import numpy as np

from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.condition import Condition
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.power_loss_factor import PowerLossFactor
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series import TimeSeries


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
        rate: TimeSeries,
        suction_pressure: TimeSeries,
        discharge_pressure: TimeSeries,
        fluid_density: TimeSeries,
        condition: Condition,
        regularity: Regularity,
        power_loss_factor: PowerLossFactor,
    ):
        self.condition = condition
        self.regularity = regularity
        self._pump_function = pump_function
        self.rate = rate
        self.suction_pressure = suction_pressure
        self.discharge_pressure = discharge_pressure
        self.fluid_density = fluid_density

        # Typically used for power line loss subsea et.c.
        self.power_loss_factor = power_loss_factor

    def evaluate(self, expression_evaluator: ExpressionEvaluator) -> ConsumerFunctionResult:
        """Evaluate the pump consumer function

        Args:
            variables_map: Variables map is the VariablesMap-object holding all the data to be evaluated.
            regularity: The regularity of the pump consumer function (same as for installation pump is part of)

        Returns:
            Pump consumer function result
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        stream_day_rate = self.condition.apply_to_array(
            input_array=Rates.to_stream_day(
                calendar_day_rates=self.rate.get_values_array(),
                regularity=self.regularity.get_values,
            )
        )

        # Do not input regularity to pump function. Handled outside
        energy_function_result = self._pump_function.evaluate_rate_ps_pd_density(
            rate=stream_day_rate,
            suction_pressures=self.suction_pressure.get_values_array(),
            discharge_pressures=self.discharge_pressure.get_values_array(),
            fluid_density=self.fluid_density.get_values_array(),
        )

        power_loss_factor = self.power_loss_factor.as_vector()

        pump_consumer_function_result = ConsumerFunctionResult(
            periods=self.regularity.get_periods,
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage),
            condition=self.condition.as_vector(),
            power_loss_factor=power_loss_factor,
            energy_usage=self.power_loss_factor.apply_to_array(
                energy_usage=np.asarray(energy_function_result.energy_usage),
            ),
        )
        return pump_consumer_function_result
