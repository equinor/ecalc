from enum import Enum

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger

INVALID_INPUT = np.nan


class ModelInputFailureStatus(str, Enum):
    INVALID_RATE_INPUT = "INVALID_RATE_INPUT"
    INVALID_SUCTION_PRESSURE_INPUT = "INVALID_SUCTION_PRESSURE_INPUT"
    INVALID_INTERMEDIATE_PRESSURE_INPUT = "INVALID_INTERMEDIATE_PRESSURE_INPUT"
    INVALID_DISCHARGE_PRESSURE_INPUT = "INVALID_DISCHARGE_PRESSURE_INPUT"
    NO_FAILURE = None


def validate_model_input(
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
    intermediate_pressure: NDArray[np.float64] | None = None,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    list[ModelInputFailureStatus],
]:
    # Ensure input is a NumPy array
    rate = np.array(rate, dtype=np.float64)
    suction_pressure = np.array(suction_pressure, dtype=np.float64)
    discharge_pressure = np.array(discharge_pressure, dtype=np.float64)

    indices_to_validate = _find_indices_to_validate(rate=rate)
    validated_failure_status = [ModelInputFailureStatus.NO_FAILURE] * len(suction_pressure)
    validated_rate = rate.copy()
    validated_suction_pressure = suction_pressure.copy()
    validated_discharge_pressure = discharge_pressure.copy()
    if intermediate_pressure is not None:
        intermediate_pressure = np.array(intermediate_pressure, dtype=np.float64)
        validated_intermediate_pressure = intermediate_pressure
    if len(indices_to_validate) >= 1:
        (
            tmp_rate,
            tmp_suction_pressure,
            tmp_discharge_pressure,
            tmp_intermediate_pressure,
            tmp_failure_status,
        ) = _validate_model_input(
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


def _find_indices_to_validate(rate: NDArray[np.float64]) -> list[int]:
    """Find indices of array where rate(s) are positive.
    For a 1D array, this means returning the indices where rate is positive.
    For a 2D array, this means returning the indices where at least one rate is positive (along 0-axis).
    """
    rate = np.atleast_1d(rate)  # Ensure rate is at least 1D
    return np.where(np.any(rate != 0, axis=0) if np.ndim(rate) == 2 else rate != 0)[0].tolist()


def _validate_model_input(
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
    intermediate_pressure: NDArray[np.float64] | None = None,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    list[ModelInputFailureStatus],
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
       tuple with the (potentially) updated input arrays and a failure_status describing if any input is invalid

    """
    validation_failures = [
        ModelInputFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_RATE_INPUT,
        ModelInputFailureStatus.NO_FAILURE,
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

        # Ensure invalid_rate_input is an array and not a single bool, this should be the case since using axis=0.
        assert isinstance(invalid_rate_input, np.ndarray)
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
                True,  # This is to also pick up failure_status NO_FAILURE
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
