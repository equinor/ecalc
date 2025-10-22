from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor


class ConsumerFunctionResult:
    def __init__(
        self,
        periods: Periods,
        power_loss_factor: TimeSeriesPowerLossFactor | None,
        energy_function_result: EnergyFunctionResult,
    ):
        self.periods = periods
        self._power_loss_factor = power_loss_factor
        self.energy_function_result = energy_function_result

    @property
    def is_valid(self) -> NDArray:
        return np.asarray(self.energy_function_result.is_valid)

    @property
    def _power_before_power_loss_factor(self) -> NDArray | None:
        return (
            np.asarray(self.energy_function_result.power, dtype=np.float64)
            if self.energy_function_result.power is not None
            else None
        )

    @property
    def power(self):
        if self._power_loss_factor is None:
            return self._power_before_power_loss_factor
        return (
            self._power_loss_factor.apply(np.asarray(self._power_before_power_loss_factor, dtype=np.float64))
            if self._power_before_power_loss_factor is not None
            else None
        )

    @property
    def energy_usage_before_power_loss_factor(self) -> NDArray:
        return np.asarray(self.energy_function_result.energy_usage, dtype=np.float64)

    @property
    def energy_usage(self):
        if self._power_loss_factor is None:
            return self.energy_usage_before_power_loss_factor
        return self._power_loss_factor.apply(np.asarray(self.energy_usage_before_power_loss_factor, dtype=np.float64))

    @property
    def power_loss_factor(self) -> NDArray:
        return (
            np.asarray(self._power_loss_factor.get_values(), dtype=np.float64)
            if self._power_loss_factor is not None
            else None
        )

    @property
    def energy_usage_unit(self) -> Unit:
        return self.energy_function_result.energy_usage_unit
