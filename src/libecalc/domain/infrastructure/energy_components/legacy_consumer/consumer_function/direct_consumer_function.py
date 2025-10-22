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

    def evaluate(self) -> ConsumerFunctionResult:
        energy_usage = self._energy_usage.get_stream_day_values()

        energy_function_result = EnergyFunctionGenericResult(
            energy_usage=energy_usage,
            energy_usage_unit=self.energy_usage_unit,
            power=energy_usage if self.is_electrical_consumer else None,
            power_unit=self.energy_usage_unit if self.is_electrical_consumer else None,
            allow_negative_energy_usage=self.is_electrical_consumer,
        )

        consumer_function_result = ConsumerFunctionResult(
            periods=self._energy_usage.get_periods(),
            energy_function_result=energy_function_result,
            power_loss_factor=self._power_loss_factor,
        )

        return consumer_function_result
