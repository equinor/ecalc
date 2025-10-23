from __future__ import annotations

from abc import abstractmethod
from functools import partial

import numpy as np
from numpy.typing import NDArray

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.logger import logger
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine
from libecalc.domain.process.compressor.core.train.utils.common import POWER_CALCULATION_TOLERANCE
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class CompressorModel:
    """A protocol for various compressor type energy function models."""

    @abstractmethod
    def set_evaluation_input(
        self,
        rate: NDArray[np.float64],
        fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface] | None,
        suction_pressure: NDArray[np.float64] | None,
        discharge_pressure: NDArray[np.float64] | None,
        intermediate_pressure: NDArray[np.float64] | None = None,
    ):
        """

        Args:
            rate (NDArray[np.float64]): Actual volumetric rate in [Sm3/h].
            fluid_factory (FluidFactoryInterface | list[FluidFactoryInterface] | None): Fluid
            suction_pressure (NDArray[np.float64]): Suction pressure per time step in [bara].
            discharge_pressure (NDArray[np.float64]): Discharge pressure per time step in [bara].
            intermediate_pressure (NDArray[np.float64] | None): Intermediate pressure per time step in [bara], or None.

        Returns:

        """
        ...

    @abstractmethod
    def get_consumption_type(self) -> ConsumptionType: ...

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
    def evaluate(self) -> CompressorTrainResult:
        """
        Evaluate the compressor model and calculate rate, suction pressure, and discharge pressure.

        Returns:
            CompressorTrainResult: The result of the compressor train evaluation.
        """
        raise NotImplementedError

    def check_for_undefined_stages(
        self,
    ) -> None:
        pass


class CompressorWithTurbineModel(CompressorModel):
    def __init__(
        self,
        compressor_energy_function: CompressorModel,
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

        self.compressor_model.set_evaluation_input(
            fluid_factory=self.compressor_model._fluid_factory,
            rate=np.asarray([standard_rate]),
            suction_pressure=np.asarray([suction_pressure]),
            discharge_pressure=np.asarray([discharge_pressure]),
        )
        result = self.compressor_model.evaluate()
        energy_result = result.get_energy_result()
        if energy_result.power is None or len(energy_result.power.values) == 0:
            return 0.0  # Return 0 if no power value available
        return float(energy_result.power.values[0]) - (max_power - POWER_CALCULATION_TOLERANCE)

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
        self.compressor_model.set_evaluation_input(
            fluid_factory=self.compressor_model._fluid_factory,
            rate=max_standard_rate,
            suction_pressure=suction_pressures,
            discharge_pressure=discharge_pressures,
        )
        results_max_standard_rate = self.compressor_model.evaluate()
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
