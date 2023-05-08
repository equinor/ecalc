from copy import deepcopy
from typing import List, Optional

import numpy as np
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    calculate_energy_usage_with_conditions_and_power_loss,
)
from libecalc.core.models.results import EnergyFunctionGenericResult
from libecalc.dto.types import RateType
from libecalc.dto.variables import VariablesMap


class DirectExpressionConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        data_transfer_object: dto.DirectConsumerFunction,
    ):
        expression = (
            data_transfer_object.fuel_rate
            if data_transfer_object.energy_usage_type == dto.types.EnergyUsageType.FUEL.value
            else data_transfer_object.load
        )
        condition_expression = data_transfer_object.condition
        power_loss_factor_expression = data_transfer_object.power_loss_factor
        direct_consumer_consumption_rate_type = data_transfer_object.consumption_rate_type

        self.data_transfer_object = data_transfer_object
        self._expression = expression
        self._convert_to_stream_day = direct_consumer_consumption_rate_type == RateType.CALENDAR_DAY
        self._condition_expression = condition_expression
        self._power_loss_factor_expression = power_loss_factor_expression

    @property
    def is_electrical_consumer(self) -> bool:
        return self.data_transfer_object.energy_usage_type == dto.types.EnergyUsageType.POWER

    @property
    def is_fuel_consumer(self) -> bool:
        return self.data_transfer_object.energy_usage_type == dto.types.EnergyUsageType.FUEL

    @property
    def energy_usage_unit(self) -> Unit:
        if self.is_electrical_consumer:
            return Unit.MEGA_WATT
        elif self.is_fuel_consumer:
            return Unit.STANDARD_CUBIC_METER_PER_DAY
        else:
            return Unit.NONE

    @property
    def power_unit(self) -> Optional[Unit]:
        if self.is_electrical_consumer:
            return Unit.MEGA_WATT

    def evaluate(
        self,
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> ConsumerFunctionResult:
        energy_usage_expression_evaluated = self._expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )

        energy_usage = (
            Rates.to_stream_day(
                calendar_day_rates=energy_usage_expression_evaluated,
                regularity=regularity,
            )
            if self._convert_to_stream_day
            else energy_usage_expression_evaluated
        )

        energy_function_result = EnergyFunctionGenericResult(
            energy_usage=list(energy_usage),
            energy_usage_unit=self.energy_usage_unit,
            power=list(energy_usage) if self.is_electrical_consumer else None,
            power_unit=self.power_unit if self.is_electrical_consumer else None,
        )

        conditions_and_power_loss_results = calculate_energy_usage_with_conditions_and_power_loss(
            variables_map=variables_map,
            energy_usage=deepcopy(energy_usage),
            condition_expression=self._condition_expression,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        consumer_function_result = ConsumerFunctionResult(
            time_vector=np.array(variables_map.time_vector),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_conditioning=deepcopy(energy_usage),
            condition=conditions_and_power_loss_results.condition,
            energy_usage_before_power_loss_factor=conditions_and_power_loss_results.energy_usage_after_condition_before_power_loss_factor,
            power_loss_factor=conditions_and_power_loss_results.power_loss_factor,
            energy_usage=conditions_and_power_loss_results.resulting_energy_usage,
        )

        return consumer_function_result
