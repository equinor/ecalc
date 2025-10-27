from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor


class ConsumerSystemOperationalSettingResult:
    def __init__(self, consumer_results: list[EnergyFunctionResult]):
        self.consumer_results = consumer_results
        self._consumer_energy_results = [consumer_result.get_energy_result() for consumer_result in consumer_results]

    def __len__(self) -> int:
        return len(self._consumer_energy_results[0].energy_usage)

    @property
    def energy_usage(self) -> NDArray:
        return np.sum([np.asarray(result.energy_usage.values) for result in self._consumer_energy_results], axis=0)

    @property
    def power(self) -> NDArray:
        return np.sum(
            [
                np.asarray(result.power.values)
                if result.power is not None
                else np.zeros_like(result.energy_usage.values)
                for result in self._consumer_energy_results
            ],
            axis=0,
        )

    @property
    def is_valid(self) -> NDArray:
        return np.multiply.reduce(
            [np.asarray(result.is_valid) for result in self._consumer_energy_results], axis=0
        ).astype(bool)

    @property
    def indices_outside_capacity(self) -> NDArray:
        return np.asarray([i for i, is_valid in enumerate(self.is_valid) if not is_valid])

    @property
    def indices_within_capacity(self) -> NDArray[np.float64]:
        return np.asarray([i for i, is_valid in enumerate(self.is_valid) if is_valid])


@dataclass
class SystemComponentResultWithName:
    name: str
    result: EnergyFunctionResult


class ConsumerSystemConsumerFunctionResult:
    """Class for holding results for a consumer system evaluation.

    operational_setting_used: an array - one for each time step evaluated - for which of
    the operational settings where used (in obtaining the final energy usage result)
    operational_settings: a list for each operational setting. Each element contains data
    of the operational setting, i.e. what rates/pressures/fluid densities for which consumer in
    the system
    operational_settings_results: a list for each operational setting. Each element contain
    data for the energy usage of each consumer in the system in this operational setting.
    """

    def __init__(
        self,
        operational_setting_used: NDArray,
        consumer_results: list[SystemComponentResultWithName],
        cross_over_used: NDArray | None,
        # 0 or 1 whether cross over is used for this result (1=True, 0=False)
        periods: Periods,
        power_loss_factor: TimeSeriesPowerLossFactor | None,
    ):
        self.periods = periods
        self._power_loss_factor = power_loss_factor
        self.operational_setting_used = operational_setting_used
        self.consumer_results = consumer_results
        self._energy_results = {result.name: result.result.get_energy_result() for result in consumer_results}
        self.cross_over_used = cross_over_used

    @property
    def energy_usage_before_power_loss_factor(self) -> NDArray:
        return np.sum([np.asarray(result.energy_usage.values) for result in self._energy_results.values()], axis=0)

    @property
    def energy_usage(self) -> NDArray:
        if self._power_loss_factor is not None:
            return np.asarray(self._power_loss_factor.apply(energy_usage=self.energy_usage_before_power_loss_factor))
        else:
            return self.energy_usage_before_power_loss_factor

    @property
    def power_loss_factor(self) -> NDArray | None:
        if self._power_loss_factor is None:
            return None
        return np.asarray(self._power_loss_factor.get_values())

    @property
    def _power_before_power_loss_factor(self) -> NDArray:
        return np.sum(
            [
                np.asarray(result.power.values)
                if result.power is not None
                else np.zeros_like(result.energy_usage.values)
                for result in self._energy_results.values()
            ],
            axis=0,
        )

    @property
    def power(self) -> NDArray:
        if self._power_loss_factor is not None:
            return np.asarray(self._power_loss_factor.apply(energy_usage=self._power_before_power_loss_factor))
        else:
            return self._power_before_power_loss_factor

    @property
    def is_valid(self) -> NDArray:
        return np.multiply.reduce(
            [np.asarray(result.is_valid) for result in self._energy_results.values()], axis=0
        ).astype(bool)

    @property
    def energy_usage_unit(self) -> Unit:
        units = {res.energy_usage.unit for res in self._energy_results.values()}
        assert len(units) == 1, "All energy usage results should be the same unit"
        return next(iter(units))
