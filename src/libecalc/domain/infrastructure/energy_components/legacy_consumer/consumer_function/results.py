from __future__ import annotations

from typing import Literal

from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.domain.process.core.results.base import EnergyFunctionResult


class ConsumerFunctionResult:
    def __init__(
        self,
        periods: Periods,
        is_valid: NDArray,
        energy_usage: NDArray,
        typ: Literal[ConsumerFunctionType.SINGLE] = ConsumerFunctionType.SINGLE,
        energy_usage_before_power_loss_factor: NDArray | None = None,
        power_loss_factor: NDArray | None = None,
        energy_function_result: EnergyFunctionResult = None,
        power: NDArray | None = None,
    ):
        assert isinstance(energy_function_result, EnergyFunctionResult)
        self.typ = typ
        self.periods = periods
        self.is_valid = is_valid
        self.energy_usage = energy_usage
        self.energy_usage_before_power_loss_factor = energy_usage_before_power_loss_factor
        self.power_loss_factor = power_loss_factor
        self.energy_function_result = energy_function_result
        self.power = power

    @property
    def energy_usage_unit(self) -> Unit:
        return self.energy_function_result.energy_usage_unit
