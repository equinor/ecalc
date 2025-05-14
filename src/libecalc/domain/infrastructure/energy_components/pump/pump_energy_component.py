from typing import Literal

import numpy as np

from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunctionResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    apply_power_loss_factor,
    get_condition_from_expression,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.process.pump.pump_process_unit import PumpProcessUnit
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class PumpEnergyComponent(EnergyComponent):
    def __init__(
        self,
        name: str,
        pump_process_unit: PumpProcessUnit,
        rate_expression: Expression,
        suction_pressure_expression: Expression,
        discharge_pressure_expression: Expression,
        fluid_density_expression: Expression,
        condition_expression: Expression = None,
        power_loss_factor_expression: Expression = None,
        component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP,
    ):
        self.name = name
        self.pump_process_unit = pump_process_unit
        self._rate_expression = convert_expression(rate_expression)
        self._suction_pressure_expression = convert_expression(suction_pressure_expression)
        self._discharge_pressure_expression = convert_expression(discharge_pressure_expression)
        self._fluid_density_expression = convert_expression(fluid_density_expression)
        self._condition_expression = condition_expression

        # Typically used for power line loss subsea et.c.
        self._power_loss_factor_expression = convert_expression(power_loss_factor_expression)

        self.component_type = component_type

    @property
    def id(self) -> str:
        return generate_id(self.name)

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def is_provider(self) -> bool:
        return False

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ):
        """Evaluate the pump energy component."""
        condition = get_condition_from_expression(
            expression_evaluator=expression_evaluator,
            condition_expression=self._condition_expression,
        )

        calendar_day_rate = expression_evaluator.evaluate(expression=self._rate_expression)

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        stream_day_rate = apply_condition(
            input_array=Rates.to_stream_day(
                calendar_day_rates=calendar_day_rate,
                regularity=regularity,
            ),
            condition=condition,
        )
        suction_pressure = expression_evaluator.evaluate(expression=self._suction_pressure_expression)
        discharge_pressure = expression_evaluator.evaluate(expression=self._discharge_pressure_expression)
        fluid_density = expression_evaluator.evaluate(expression=self._fluid_density_expression)

        # Do not input regularity to pump function. Handled outside
        energy_function_result = self.pump_process_unit.evaluate_rate_ps_pd_density(
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
            condition=condition,
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=np.asarray(energy_function_result.energy_usage),
                power_loss_factor=power_loss_factor,
            ),
        )
        return pump_consumer_function_result
