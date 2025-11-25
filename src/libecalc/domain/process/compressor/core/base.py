from __future__ import annotations

from functools import partial
from typing import assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.logger import logger
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.utils.common import POWER_CALCULATION_TOLERANCE
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class CompressorWithTurbineModel:
    def __init__(
        self,
        compressor_energy_function: CompressorTrainModel | CompressorModelSampled,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        turbine_model: Turbine,
    ):
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.compressor_model = compressor_energy_function
        self.turbine_model = turbine_model

    def set_evaluation_input(
        self,
        *args,
        **kwargs,
    ):
        self.compressor_model.set_evaluation_input(*args, **kwargs)

    def get_consumption_type(self) -> ConsumptionType:
        return ConsumptionType.FUEL

    def evaluate(
        self,
    ) -> CompressorTrainResult:
        compressor_model_result = self.compressor_model.evaluate()
        turbine_result = self.evaluate_turbine_based_on_compressor_model_result(compressor_model_result)
        return turbine_result

    def evaluate_turbine_based_on_compressor_model_result(
        self, compressor_energy_function_result: CompressorTrainResult
    ) -> CompressorTrainResult:
        energy_result = compressor_energy_function_result.get_energy_result()
        if energy_result.power is not None:
            # The compressor energy function evaluates to a power load in this case
            load_adjusted = np.where(
                np.asarray(energy_result.power.values) > 0,
                np.asarray(energy_result.power.values) * self._energy_usage_adjustment_factor
                + self._energy_usage_adjustment_constant,
                np.asarray(energy_result.power.values),
            )
            turbine_result = self.turbine_model.evaluate(load=load_adjusted)
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

        compressor_model = self.compressor_model
        if isinstance(compressor_model, CompressorTrainModel):
            compressor_model.set_evaluation_input(
                fluid_factory=compressor_model._fluid_factory,
                rate=np.asarray([standard_rate]),
                suction_pressure=np.asarray([suction_pressure]),
                discharge_pressure=np.asarray([discharge_pressure]),
            )
        elif isinstance(compressor_model, CompressorModelSampled):
            compressor_model.set_evaluation_input(
                rate=np.asarray([standard_rate]),
                suction_pressure=np.asarray([suction_pressure]),
                discharge_pressure=np.asarray([discharge_pressure]),
            )
        else:
            assert_never(compressor_model)

        result = compressor_model.evaluate()
        energy_result = result.get_energy_result()
        if energy_result.power is None or len(energy_result.power.values) == 0:
            return 0.0  # Return 0 if no power value available
        return float(energy_result.power.values[0]) - (max_power - POWER_CALCULATION_TOLERANCE)

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_factory: FluidFactoryInterface | None = None,
    ) -> NDArray[np.float64]:
        """Validate that the compressor has enough power to handle the set maximum standard rate.
        If there is insufficient power find new maximum rate.
        """
        compressor_model = self.compressor_model
        if fluid_factory is not None:
            compressor_model._fluid_factory = fluid_factory

        max_standard_rate = compressor_model.get_max_standard_rate(
            suction_pressures=suction_pressures, discharge_pressures=discharge_pressures
        )
        assert max_standard_rate is not None
        # Check if the obtained results are within the maximum load that the turbine can deliver
        if isinstance(compressor_model, CompressorTrainModel):
            compressor_model.set_evaluation_input(
                fluid_factory=compressor_model._fluid_factory,
                rate=max_standard_rate,
                suction_pressure=suction_pressures,
                discharge_pressure=discharge_pressures,
            )
        elif isinstance(compressor_model, CompressorModelSampled):
            compressor_model.set_evaluation_input(
                rate=max_standard_rate,
                suction_pressure=suction_pressures,
                discharge_pressure=discharge_pressures,
            )
        else:
            assert_never(compressor_model)

        results_max_standard_rate = compressor_model.evaluate()
        energy_result = results_max_standard_rate.get_energy_result()

        max_power = self.turbine_model.max_power

        if energy_result.power is not None:
            powers = np.asarray(energy_result.power.values)
            for i, (power, suction_pressure, discharge_pressure) in enumerate(
                zip(powers, suction_pressures, discharge_pressures)
            ):
                if not np.isnan(power) and power > max_power:
                    max_standard_rate[i] = find_root(
                        lower_bound=0,
                        upper_bound=max_standard_rate[i],
                        func=partial(
                            self._calculate_remaining_capacity_in_train_given_standard_rate,
                            suction_pressure=suction_pressure,
                            discharge_pressure=discharge_pressure,
                            max_power=max_power,  # type: ignore[arg-type]
                        ),
                    )

        return max_standard_rate

    def get_requested_inlet_pressure(self) -> NDArray[np.float64]:
        return self.compressor_model._suction_pressure

    def get_requested_outlet_pressure(self) -> NDArray[np.float64]:
        return self.compressor_model._discharge_pressure
