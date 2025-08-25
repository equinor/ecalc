import numpy as np

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.units import Unit
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.process.core.results import EnergyFunctionGenericResult
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_power import TimeSeriesPower
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor


class DirectConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        fuel_rate: TimeSeriesFlowRate | None = None,
        load: TimeSeriesPower | None = None,
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
    ):
        self._energy_usage = fuel_rate if energy_usage_type == EnergyUsageType.FUEL.value else load
        self._energy_usage_type = energy_usage_type
        self._power_loss_factor = power_loss_factor

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

    def evaluate(self) -> ConsumerFunctionResult:
        energy_usage = self._energy_usage.get_stream_day_values()

        energy_function_result = EnergyFunctionGenericResult(
            energy_usage=energy_usage,
            energy_usage_unit=self.energy_usage_unit,
            power=energy_usage if self.is_electrical_consumer else None,
            power_unit=self.power_unit if self.is_electrical_consumer else None,
        )

        if self._power_loss_factor is not None:
            energy_usage = self._power_loss_factor.apply(
                energy_usage=np.asarray(energy_function_result.energy_usage, dtype=np.float64)
            )
            power_loss_factor = self._power_loss_factor.get_values()
        else:
            energy_usage = energy_function_result.energy_usage
            power_loss_factor = None

        is_valid = np.asarray(energy_function_result.is_valid)

        # Invalidate negative fuel rates after applying conditions.
        # Direct consumers can use LOAD (electrical consumers) or FUELRATE (fuel consumers).
        # Note: Negative load values can be valid in some cases (e.g., energy efficiency measures on generator sets),
        # but negative fuel rates are always invalid.

        if self.is_fuel_consumer:
            is_valid[np.asarray(energy_usage) < 0] = False

        consumer_function_result = ConsumerFunctionResult(
            periods=self._energy_usage.get_periods(),
            is_valid=is_valid,
            energy_function_result=energy_function_result,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage, dtype=np.float64),
            power_loss_factor=np.asarray(power_loss_factor, dtype=np.float64),
            energy_usage=np.asarray(energy_usage, dtype=np.float64),
        )

        return consumer_function_result
