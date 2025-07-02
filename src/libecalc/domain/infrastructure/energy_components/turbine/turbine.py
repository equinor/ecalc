from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.units import Unit
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessTurbineEfficiencyValidationException,
)
from libecalc.domain.process.core.results import TurbineResult
from libecalc.presentation.yaml.validation_errors import Location

SECONDS_PER_DAY = 86400


class Turbine:
    typ = EnergyModelType.TURBINE

    def __init__(
        self,
        loads: list[float],
        lower_heating_value: float,
        efficiency_fractions: list[float],
        energy_usage_adjustment_factor: float,
        energy_usage_adjustment_constant: float,
    ):
        self.lower_heating_value = lower_heating_value
        self.loads = loads
        self._maximum_load = max(self.loads)
        self.efficiency_fractions = efficiency_fractions
        self.validate_loads_and_efficiency_factors()
        self._efficiency_function = interp1d(
            x=self.loads,
            y=self.efficiency_fractions,
            bounds_error=False,
            fill_value=(0, self.efficiency_fractions[-1]),
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
            fuel_lower_heating_value if fuel_lower_heating_value > 0 else self.lower_heating_value
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

        # Convert arrays to lists, providing empty lists as fallback for None values
        load_list = array_to_list(load_adjusted) or []
        efficiency_list = array_to_list(efficiency) or []  # type: ignore[arg-type]
        fuel_usage_list = array_to_list(fuel_usage) or []
        exceeds_max_list = array_to_list(load > self._maximum_load) or []

        return TurbineResult(
            load=load_list,
            efficiency=efficiency_list,
            fuel_rate=fuel_usage_list,
            energy_usage=fuel_usage_list,
            energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=load_list,
            power_unit=Unit.MEGA_WATT,
            exceeds_maximum_load=exceeds_max_list,
        )

    def validate_loads_and_efficiency_factors(self):
        if len(self.loads) != len(self.efficiency_fractions):
            msg = (
                f"Need equal number of load and efficiency values for turbine model. "
                f"Got {len(self.loads)} load values and {len(self.efficiency_fractions)} efficiency values."
            )
            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

        invalid_efficiencies = [x for x in self.efficiency_fractions if not 0 <= x <= 1]
        if invalid_efficiencies:
            msg = f"Turbine efficiency fraction should be a number between 0 and 1. Invalid values: {invalid_efficiencies}"
            raise ProcessTurbineEfficiencyValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
