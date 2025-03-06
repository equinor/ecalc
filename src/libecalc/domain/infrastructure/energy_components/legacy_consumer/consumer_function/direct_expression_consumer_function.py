import numpy as np

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    apply_power_loss_factor,
    get_condition_from_expression,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.process.core.results import EnergyFunctionGenericResult
from libecalc.expression import Expression


class DirectExpressionConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        condition: Expression | None = None,
        fuel_rate: Expression | None = None,
        load: Expression | None = None,
        power_loss_factor: Expression | None = None,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
    ):
        expression = fuel_rate if energy_usage_type == EnergyUsageType.FUEL.value else load
        condition_expression = condition
        power_loss_factor_expression = power_loss_factor
        direct_consumer_consumption_rate_type = consumption_rate_type
        self._energy_usage_type = energy_usage_type
        self._expression = expression
        self._convert_to_stream_day = RateType(direct_consumer_consumption_rate_type.value) == RateType.CALENDAR_DAY
        self._condition_expression = condition_expression
        self._power_loss_factor_expression = power_loss_factor_expression

    @property
    def is_electrical_consumer(self) -> bool:
        return self._energy_usage_type == EnergyUsageType.POWER

    @property
    def is_fuel_consumer(self) -> bool:
        return self._energy_usage_type == EnergyUsageType.FUEL

    @property
    def energy_usage_unit(self) -> Unit:
        if self.is_electrical_consumer:
            return Unit.MEGA_WATT
        elif self.is_fuel_consumer:
            return Unit.STANDARD_CUBIC_METER_PER_DAY
        else:
            return Unit.NONE

    @property
    def power_unit(self) -> Unit | None:
        if self.is_electrical_consumer:
            return Unit.MEGA_WATT
        return None

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> ConsumerFunctionResult:
        energy_usage_expression_evaluated = expression_evaluator.evaluate(expression=self._expression)

        # Do conditioning first - set rates to zero if conditions are not met
        condition = get_condition_from_expression(
            expression_evaluator=expression_evaluator,
            condition_expression=self._condition_expression,
        )

        energy_usage = apply_condition(
            input_array=Rates.to_stream_day(
                calendar_day_rates=energy_usage_expression_evaluated,
                regularity=regularity,
            )
            if self._convert_to_stream_day
            else energy_usage_expression_evaluated,
            condition=condition,
        )

        energy_function_result = EnergyFunctionGenericResult(
            energy_usage=array_to_list(energy_usage),
            energy_usage_unit=self.energy_usage_unit,
            power=array_to_list(energy_usage) if self.is_electrical_consumer else None,
            power_unit=self.power_unit if self.is_electrical_consumer else None,
        )

        power_loss_factor = get_power_loss_factor_from_expression(
            expression_evaluator=expression_evaluator,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        is_valid = np.asarray(energy_function_result.is_valid)

        # Invalidate negative fuel rates after applying conditions.
        # Direct consumers can use LOAD (electrical consumers) or FUELRATE (fuel consumers).
        # Note: Negative load values can be valid in some cases (e.g., energy efficiency measures on generator sets),
        # but negative fuel rates are always invalid.

        if self.is_fuel_consumer:
            is_valid[energy_usage < 0] = False

        consumer_function_result = ConsumerFunctionResult(
            periods=expression_evaluator.get_periods(),
            is_valid=is_valid,
            energy_function_result=energy_function_result,
            condition=condition,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage),
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=np.asarray(energy_function_result.energy_usage),
                power_loss_factor=power_loss_factor,
            ),
        )

        return consumer_function_result
