from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.list.list_utils import array_to_list
from libecalc.common.units import Unit
from libecalc.domain.process.core.results import TurbineResult

SECONDS_PER_DAY = 86400


class TurbineModel:
    def __init__(
        self,
        loads: list[float],
        lower_heating_value: float,
        efficiency_fractions: list[float],
        energy_usage_adjustment_factor: float,
        energy_usage_adjustment_constant: float,
    ):
        self.fuel_lower_heating_value = np.array(lower_heating_value)
        load_values = np.array(loads)
        self._maximum_load = load_values.max()
        efficiency_values = np.array(efficiency_fractions)
        self._efficiency_function = interp1d(
            x=load_values,
            y=efficiency_values,
            bounds_error=False,
            fill_value=(0, efficiency_values[-1]),
        )
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant

    @property
    def max_power(self) -> float | None:
        return self._maximum_load * self._energy_usage_adjustment_factor - self._energy_usage_adjustment_constant

    def evaluate(self, load: NDArray[np.float64], fuel_lower_heating_value: float = 0) -> TurbineResult:
        # Calibration of turbine load:
        # Linear adjustment: (1/a)*x + b/a.
        load_adjusted = np.where(
            load > 0,
            (load + self._energy_usage_adjustment_constant) / self._energy_usage_adjustment_factor,
            load,
        )
        lower_heating_value_to_use = (
            fuel_lower_heating_value if fuel_lower_heating_value > 0 else self.fuel_lower_heating_value
        )
        efficiency = self._efficiency_function(x=load_adjusted)

        # To avoid divide by zero we use np.divide with out array and where clause.
        fuel_usage = np.divide(
            np.divide(
                load_adjusted * SECONDS_PER_DAY,
                lower_heating_value_to_use,
                out=np.zeros_like(load_adjusted),
                where=lower_heating_value_to_use != 0,
            ),
            efficiency,
            out=np.zeros_like(load_adjusted),
            where=np.logical_and(lower_heating_value_to_use != 0, efficiency != 0),
        )

        return TurbineResult(
            load=array_to_list(load_adjusted),
            efficiency=array_to_list(efficiency),
            fuel_rate=array_to_list(fuel_usage),
            energy_usage=array_to_list(fuel_usage),
            energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=array_to_list(load_adjusted),
            power_unit=Unit.MEGA_WATT,
            exceeds_maximum_load=array_to_list(load > self._maximum_load),
        )
