import numpy as np

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.condition import Condition
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.power_loss_factor import PowerLossFactor
from libecalc.domain.process.core.results import EnergyFunctionGenericResult
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series import TimeSeries


class DirectExpressionConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        condition: Condition,
        regularity: Regularity,
        power_loss_factor: PowerLossFactor,
        fuel_rate: TimeSeries | None = None,
        load: TimeSeries | None = None,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
    ):
        self.energy_usage = fuel_rate if energy_usage_type == EnergyUsageType.FUEL.value else load
        self.power_loss_factor = power_loss_factor
        self.condition = condition
        self.regularity = regularity
        assert isinstance(consumption_rate_type, RateType)
        self._energy_usage_type = energy_usage_type
        self._convert_to_stream_day = consumption_rate_type == RateType.CALENDAR_DAY

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
    ) -> ConsumerFunctionResult:
        energy_usage = self.condition.apply_to_array_as_list(
            input_array=(
                Rates.to_stream_day(
                    calendar_day_rates=self.energy_usage.get_values_array(),
                    regularity=self.regularity.get_values,
                )
                if self._convert_to_stream_day
                else self.energy_usage.get_values_array()
            )
        )

        energy_function_result = EnergyFunctionGenericResult(
            energy_usage=energy_usage,
            energy_usage_unit=self.energy_usage_unit,
            power=energy_usage if self.is_electrical_consumer else None,
            power_unit=self.power_unit if self.is_electrical_consumer else None,
        )

        power_loss_factor = self.power_loss_factor.as_vector()

        is_valid = np.asarray(energy_function_result.is_valid)

        # Invalidate negative fuel rates after applying conditions.
        # Direct consumers can use LOAD (electrical consumers) or FUELRATE (fuel consumers).
        # Note: Negative load values can be valid in some cases (e.g., energy efficiency measures on generator sets),
        # but negative fuel rates are always invalid.

        if self.is_fuel_consumer:
            is_valid[np.asarray(energy_usage) < 0] = False

        consumer_function_result = ConsumerFunctionResult(
            periods=self.regularity.get_periods,
            is_valid=is_valid,
            energy_function_result=energy_function_result,
            condition=self.condition.as_vector(),
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage),
            power_loss_factor=power_loss_factor,
            energy_usage=self.power_loss_factor.apply_to_array(
                energy_usage=np.asarray(energy_function_result.energy_usage),
            ),
        )

        return consumer_function_result
