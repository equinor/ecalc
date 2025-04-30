from __future__ import annotations

from abc import abstractmethod
from functools import partial

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.train.utils.common import (
    POWER_CALCULATION_TOLERANCE,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.turbine import TurbineModel


class CompressorModel:
    """A protocol for various compressor type energy function models."""

    @abstractmethod
    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Get the maximum standard flow rate [Sm3/day] for the compressor train. This method is valid for compressor
        trains where there are a single input stream and no streams are added or removed in the train.

        :param suction_pressures: Suction pressure per time step [bara]
        :param discharge_pressures: Discharge pressure per time step [bara]
        :return: Maximum standard rate per day per time-step [Sm3/day]
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ) -> CompressorTrainResult:
        """
        Evaluate the compressor model and calculate rate, suction pressure, and discharge pressure.

        Args:
            rate (NDArray[np.float64]): Actual volumetric rate in [Sm3/h].
            suction_pressure (NDArray[np.float64]): Suction pressure per time step in [bara].
            discharge_pressure (NDArray[np.float64]): Discharge pressure per time step in [bara].
            intermediate_pressure (NDArray[np.float64] | None): Intermediate pressure per time step in [bara], or None.

        Returns:
            CompressorTrainResult: The result of the compressor train evaluation.
        """
        raise NotImplementedError

    def check_for_undefined_stages(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> None:
        pass


class CompressorWithTurbineModel(CompressorModel):
    def __init__(
        self,
        compressor_energy_function: CompressorModel,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        turbine_model: TurbineModel,
    ):
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.compressor_model = compressor_energy_function
        self.turbine_model = turbine_model

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ) -> CompressorTrainResult:
        return self.evaluate_turbine_based_on_compressor_model_result(
            compressor_energy_function_result=self.compressor_model.evaluate(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                intermediate_pressure=intermediate_pressure,
            )
        )

    def evaluate_turbine_based_on_compressor_model_result(
        self, compressor_energy_function_result: CompressorTrainResult
    ) -> CompressorTrainResult:
        if compressor_energy_function_result.power is not None:
            # The compressor energy function evaluates to a power load in this case
            load_adjusted = np.where(
                np.asarray(compressor_energy_function_result.power) > 0,
                np.asarray(compressor_energy_function_result.power) * self._energy_usage_adjustment_factor
                + self._energy_usage_adjustment_constant,
                np.asarray(compressor_energy_function_result.power),
            )
            turbine_result = self.turbine_model.evaluate(load=load_adjusted)
            compressor_energy_function_result.energy_usage = turbine_result.fuel_rate
            compressor_energy_function_result.energy_usage_unit = Unit.STANDARD_CUBIC_METER_PER_DAY
            compressor_energy_function_result.power = turbine_result.load
            compressor_energy_function_result.power_unit = Unit.MEGA_WATT
            compressor_energy_function_result.turbine_result = turbine_result
        else:
            logger.warning(
                "Compressor in compressor with turbine did not return power values." " Turbine will not be computed."
            )

        return compressor_energy_function_result

    def _calculate_remaining_capacity_in_train_given_standard_rate(
        self, standard_rate: float, suction_pressure: float, discharge_pressure: float, max_power: float
    ) -> float:
        """Expression used in optimization to find the rate that utilizes the compressor trains capacity."""
        return self.compressor_model.evaluate(
            rate=np.asarray([standard_rate]),
            suction_pressure=np.asarray([suction_pressure]),
            discharge_pressure=np.asarray([discharge_pressure]),
        ).power[0] - (max_power - POWER_CALCULATION_TOLERANCE)

    def get_max_standard_rate(
        self, suction_pressures: NDArray[np.float64], discharge_pressures: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Validate that the compressor has enough power to handle the set maximum standard rate.
        If there is insufficient power find new maximum rate.
        """
        max_standard_rate = self.compressor_model.get_max_standard_rate(
            suction_pressures=suction_pressures, discharge_pressures=discharge_pressures
        )

        # Check if the obtained results are within the maximum load that the turbine can deliver
        results_max_standard_rate = self.compressor_model.evaluate(
            rate=max_standard_rate,
            suction_pressure=suction_pressures,
            discharge_pressure=discharge_pressures,
        )
        max_power = self.turbine_model.max_power

        if results_max_standard_rate.power is not None:
            for i, (power, suction_pressure, discharge_pressure) in enumerate(
                zip(results_max_standard_rate.power, suction_pressures, discharge_pressures)
            ):
                if power > max_power:
                    max_standard_rate[i] = find_root(
                        lower_bound=0,
                        upper_bound=max_standard_rate[i],
                        func=partial(
                            self._calculate_remaining_capacity_in_train_given_standard_rate,
                            suction_pressure=suction_pressure,
                            discharge_pressure=discharge_pressure,
                            max_power=max_power,
                        ),
                    )

        return max_standard_rate
