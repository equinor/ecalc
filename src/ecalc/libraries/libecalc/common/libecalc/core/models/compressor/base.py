from __future__ import annotations

from abc import abstractmethod
from functools import partial
from typing import List, Optional, Tuple

import numpy as np
from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.core.models.base import BaseModel
from libecalc.core.models.compressor.train.utils.common import (
    POWER_CALCULATION_TOLERANCE,
)
from libecalc.core.models.compressor.train.utils.numeric_methods import find_root
from libecalc.core.models.results import CompressorTrainResult
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.core.models.turbine import TurbineModel
from numpy.typing import NDArray


class CompressorModel(BaseModel):
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
    def evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> CompressorTrainResult:
        """Evaluate the compressor model and get rate, suction pressure and discharge pressure.

        :param rate: Actual volumetric rate [Sm3/h]
        :param suction_pressure: Suction pressure per time step  [bara]
        :param discharge_pressure: Discharge pressure per time step bar [bara]
        """
        raise NotImplementedError

    def validate_operational_conditions(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: Optional[NDArray[np.float64]] = None,
    ) -> Tuple[
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
        List[CompressorTrainCommonShaftFailureStatus],
    ]:
        indices_to_validate = self._find_indices_to_validate(rate=rate)
        validated_failure_status = [None] * len(suction_pressure)
        validated_rate = rate.copy()
        validated_suction_pressure = suction_pressure.copy()
        validated_discharge_pressure = discharge_pressure.copy()
        if intermediate_pressure is not None:
            validated_intermediate_pressure = intermediate_pressure
        if len(indices_to_validate) >= 1:
            (
                tmp_rate,
                tmp_suction_pressure,
                tmp_discharge_pressure,
                tmp_intermediate_pressure,
                tmp_failure_status,
            ) = self._validate_operational_conditions(
                rate=rate[:, indices_to_validate] if np.ndim(rate) == 2 else rate[indices_to_validate],
                suction_pressure=suction_pressure[indices_to_validate],
                discharge_pressure=discharge_pressure[indices_to_validate],
                intermediate_pressure=intermediate_pressure[indices_to_validate]
                if intermediate_pressure is not None
                else None,
            )

            if np.ndim(rate) == 2:
                validated_rate[:, indices_to_validate] = tmp_rate
            else:
                validated_rate[indices_to_validate] = tmp_rate
            validated_suction_pressure[indices_to_validate] = tmp_suction_pressure
            validated_discharge_pressure[indices_to_validate] = tmp_discharge_pressure
            if intermediate_pressure is not None:
                validated_intermediate_pressure[indices_to_validate] = tmp_intermediate_pressure
            for i, failure in enumerate(tmp_failure_status):
                validated_failure_status[indices_to_validate[i]] = failure

        # any remaining zero or negative suction/discharge pressures (for unvalidated time steps, others are already changed)
        # must be set to 1 (for neqsim to initiate fluid streams)
        validated_suction_pressure = np.where(validated_suction_pressure <= 0, 1, validated_suction_pressure)
        validated_discharge_pressure = np.where(validated_discharge_pressure <= 0, 1, validated_discharge_pressure)

        return (
            validated_rate,
            validated_suction_pressure,
            validated_discharge_pressure,
            validated_intermediate_pressure if intermediate_pressure is not None else None,
            validated_failure_status,
        )

    @staticmethod
    def _find_indices_to_validate(rate: NDArray[np.float64]) -> List[int]:
        """Find indices of array where rate(s) are positive.
        For a 1D array, this means returning the indices where rate is positive.
        For a 2D array, this means returning the indices where at least one rate is positive (along 0-axis).
        """
        return np.where(np.any(rate != 0, axis=0) if np.ndim(rate) == 2 else rate != 0)[0].tolist()

    @staticmethod
    def _validate_operational_conditions(
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: Optional[NDArray[np.float64]] = None,
    ) -> Tuple[
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
        List[CompressorTrainCommonShaftFailureStatus],
    ]:
        """
        Checks for negative or zero values in the input values to the compressor train.

        The following is done:
            - Time steps where rate is zero are not checked for validity
              (but zero or negative pressures will still be changed to 1)
            - Any pressures that are negative or zero are set to one, and all rates for that time step are set to zero
            - Any negative rates are set to zero
            - A failure_status describing the first failure encountered is returned

        Returns only one failure_status. Checks the potential failures at each time step in the following order:
        suction pressure, intermediate_pressure, discharge pressure and rate. If there are multiple failures,
        only the first one will be returned. When the input is changed to fix the first failure, the next failure
        will be reported, and so on.

        Args:
            rate: Input rate(s) to the compressor train
            suction_pressure: Suction pressures for the compressor train
            discharge_pressure: Discharge pressures for the compressor train
            intermediate_pressure: Intermediate pressures for the compressor train (if any)

        Returns:
            Tuple with the (potentially) updated input arrays and a failure_status describing if any input is invalid

        """
        validation_failures = [
            CompressorTrainCommonShaftFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
            CompressorTrainCommonShaftFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
            CompressorTrainCommonShaftFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
            CompressorTrainCommonShaftFailureStatus.INVALID_RATE_INPUT,
            None,
        ]

        input_rate = rate.copy()
        input_suction_pressure = suction_pressure.copy()
        input_intermediate_pressure = intermediate_pressure.copy() if intermediate_pressure is not None else None
        input_discharge_pressure = discharge_pressure.copy()

        if not np.all(rate >= 0):
            logger.warning(
                f"The rate(s) in the compressor train must have non negative values. Given values [Sm3/sd]: "
                f"{rate.tolist()}. The affected time steps will not be calculated, and rate is set to zero."
            )
            rate = (
                np.where(np.any(rate < 0, axis=0), 0, rate) if np.ndim(rate) == 2 else np.where(rate < 0, 0, rate)
            )  # if the rate for one stream is negative, set the rates for all streams to zero for that time step
        if intermediate_pressure is not None:
            if not np.all(intermediate_pressure > 0):
                logger.warning(
                    f"Interstage pressure needs to be a positive value. Given values: {intermediate_pressure.tolist()}."
                    f" The affected time steps will not be calculated, and rate is set to zero."
                )
                rate = np.where(intermediate_pressure <= 0, 0, rate)
                intermediate_pressure = np.where(intermediate_pressure <= 0, 1, intermediate_pressure)
        if not np.all(suction_pressure > 0):
            logger.warning(
                f"Inlet pressure needs to be a positive value. Given values: {suction_pressure.tolist()}."
                f" The affected time steps will not be calculated, and rate is set to zero."
            )
            rate = np.where(suction_pressure <= 0, 0, rate)
            suction_pressure = np.where(suction_pressure <= 0, 1, suction_pressure)
        if not np.all(discharge_pressure > 0):
            logger.warning(
                f"Outlet pressure needs to be a positive value. Given values: {discharge_pressure.tolist()}"
                f" The affected time steps will not be calculated, and rate is set to zero."
            )
            rate = np.where(discharge_pressure <= 0, 0, rate)
            discharge_pressure = np.where(discharge_pressure <= 0, 1, discharge_pressure)
        if not np.all(discharge_pressure >= suction_pressure):
            logger.warning(
                f"Inlet pressure needs to be a less than or equal to outlet pressure. Given values for inlet"
                f" pressure: {suction_pressure.tolist()}. Given values for outlet pressure:"
                f" {discharge_pressure.tolist()}. The affected time steps will not be calculated,"
                f" and rate is set to zero."
            )
            rate = np.where(discharge_pressure < suction_pressure, 0, rate)
        # for multiple stream train, rate is 2D
        if np.ndim(rate) == 2:
            # check if any of the streams have changed value during validation, streams along axis 0, time along axis 1
            invalid_rate_input = np.any(rate != input_rate, axis=0)
        else:
            invalid_rate_input = np.where(rate != input_rate, True, False)

        invalid_suction_pressure_input = np.logical_or(
            np.where(suction_pressure != input_suction_pressure, True, False),
            np.where(suction_pressure > discharge_pressure, True, False),
        )
        invalid_discharge_pressure_input = np.where(discharge_pressure != input_discharge_pressure, True, False)
        invalid_intermediate_pressure_input = (
            np.where(intermediate_pressure != input_intermediate_pressure, True, False)
            if intermediate_pressure is not None
            else np.asarray([False] * len(suction_pressure))
        )

        failure_status = [
            validation_failures[
                [
                    invalid_suction_pressure,
                    invalid_intermediate_pressure,
                    invalid_discharge_pressure,
                    invalid_rate,
                    True,  # This is to also pick up failure_status None
                ].index(True)
            ]
            for invalid_rate, invalid_suction_pressure, invalid_intermediate_pressure, invalid_discharge_pressure in zip(
                invalid_rate_input,
                invalid_suction_pressure_input,
                invalid_intermediate_pressure_input,
                invalid_discharge_pressure_input,
            )
        ]

        return rate, suction_pressure, discharge_pressure, intermediate_pressure, failure_status


class CompressorWithTurbineModel(CompressorModel):
    def __init__(
        self,
        data_transfer_object: dto.CompressorWithTurbine,
        compressor_energy_function: CompressorModel,
        turbine_model: TurbineModel,
    ):
        self.data_transfer_object = data_transfer_object
        self.compressor_model = compressor_energy_function
        self.turbine_model = turbine_model

    def evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> CompressorTrainResult:
        return self.evaluate_turbine_based_on_compressor_model_result(
            compressor_energy_function_result=self.compressor_model.evaluate_rate_ps_pd(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        )

    def evaluate_rate_ps_pint_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> CompressorTrainResult:
        return self.evaluate_turbine_based_on_compressor_model_result(
            compressor_energy_function_result=self.compressor_model.evaluate_rate_ps_pint_pd(
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
                np.asarray(compressor_energy_function_result.power)
                + self.data_transfer_object.energy_usage_adjustment_constant,
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
        return self.compressor_model.evaluate_rate_ps_pd(
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
        results_max_standard_rate = self.compressor_model.evaluate_rate_ps_pd(
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
