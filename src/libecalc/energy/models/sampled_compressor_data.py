"""Validates a sampled-compressor's raw sample-table inputs and derives
SampledCompressorData from them: this is the shared constructor contract every
SampledCompressor leaf class (in sampled_compressor.py) and SampledCompressorFactory
(in sampled_compressor_factory.py) is built from or around. Kept in its own module,
below both, so neither depends on the other at runtime for this type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.ecalc_validation_error import (
    ProcessEqualLengthValidationException,
    ProcessMissingVariableValidationException,
    ProcessNegativeValuesValidationException,
)
from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.energy.models.convex_hull import FloatArray
from libecalc.energy.models.fuel_power_curve import FuelPowerCurve

VariableName = Literal["RATE", "SUCTION_PRESSURE", "DISCHARGE_PRESSURE"]

RATE_NAME: VariableName = "RATE"
PS_NAME: VariableName = "SUCTION_PRESSURE"
PD_NAME: VariableName = "DISCHARGE_PRESSURE"


def _as_float_array(values: list[float] | NDArray[np.float64]) -> FloatArray:
    return np.asarray(values, dtype=np.float64)


def _require_strictly_monotonic_fuel_power_samples(
    fuel_values: FloatArray, power_values: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """Deduplicates exact-duplicate (fuel, power) rows, sorts by fuel, and requires both
    to come out strictly increasing (a genuine, invertible one-to-one mapping). A table
    where the same fuel maps to different power (or vice versa) is rejected rather than
    silently resolved - a deliberate choice for the new energy domain."""
    unique_pairs = np.unique(np.column_stack([fuel_values, power_values]), axis=0)
    sorted_fuel, sorted_power = unique_pairs[:, 0], unique_pairs[:, 1]
    if np.any(np.diff(sorted_fuel) <= 0) or np.any(np.diff(sorted_power) <= 0):
        raise IllegalStateException(
            "power_interpolation_values must be a strictly monotonic function of "
            "energy_usage_values (after removing exact-duplicate sample rows): each "
            "distinct fuel value must map to exactly one power value and vice versa, "
            "so the fuel<->power relationship is invertible in both directions."
        )
    return sorted_fuel, sorted_power


def _validate_raw_lists(
    energy_usage_values: list[float],
    rate_values: list[float] | None,
    suction_pressure_values: list[float] | None,
    discharge_pressure_values: list[float] | None,
    power_interpolation_values: list[float] | None,
) -> None:
    if not rate_values and not suction_pressure_values and not discharge_pressure_values:
        raise ProcessMissingVariableValidationException(
            message="Need at least one variable for CompressorTrainSampled (rate, suction_pressure or discharge_pressure)"
        )
    count = len(energy_usage_values)
    named_values = (
        ("energy_usage_values", energy_usage_values),
        ("rate_values", rate_values),
        ("suction_pressure_values", suction_pressure_values),
        ("discharge_pressure_values", discharge_pressure_values),
        ("power_interpolation_values", power_interpolation_values),
    )
    for name, values in named_values:
        if name != "energy_usage_values" and values is not None and len(values) != count:
            raise ProcessEqualLengthValidationException(
                message=f"{name} has wrong number of points. Should have {count} (equal to number of energy usage value points)"
            )
    for name, values in named_values:
        if values is None:
            continue
        numeric_values: list[float] = []
        for row_index, value in enumerate(values):
            try:
                numeric_values.append(float(value))
            except (TypeError, ValueError) as error:
                raise InvalidColumnException(
                    header=name,
                    message=f"Got non-numeric value '{value}'.",
                    row_index=row_index,
                ) from error
        if any(value < 0 for value in numeric_values):
            raise ProcessNegativeValuesValidationException(
                message=f"All values in {name} must be greater than or equal to 0"
            )


def _determine_active_variables(
    provided_variables: dict[VariableName, FloatArray],
) -> tuple[VariableName, ...]:
    """Which of the provided variables actually vary (are not constant) across the
    sample table - the other(s), if any, are degenerate and dropped from the model.
    Order always follows RATE -> SUCTION_PRESSURE -> DISCHARGE_PRESSURE priority, since
    provided_variables is itself always built in that order."""
    return tuple(name for name, values in provided_variables.items() if np.unique(values).size != 1)


@dataclass(frozen=True, eq=False)
class SampledCompressorData:
    """Validated, derived state built once from a SampledCompressor's raw sample-table
    inputs: each variable's raw values (unfiltered - degenerate or not), which of those
    variables turned out non-degenerate ("active"), each degenerate variable's clamp
    limit, and the optional fuel/power curve. from_raw_lists() runs all
    validation up front, so every leaf class and SampledCompressorFactory can build one
    and treat it as already-valid.

    eq/hash are left at object identity (eq=False) rather than derived: several fields
    are lists/dicts/ndarrays, which are unhashable and whose "==" raises on ndarrays
    rather than returning a bool - so a derived __eq__/__hash__ would be broken anyway."""

    energy_usage_values: list[float]
    rate_values: list[float] | None
    suction_pressure_values: list[float] | None
    discharge_pressure_values: list[float] | None
    power_interpolation_values: list[float] | None
    provided_variables: dict[VariableName, FloatArray]
    required_variables: list[VariableName]
    active_variables: tuple[VariableName, ...]
    degenerated_rate: float
    degenerated_ps: float
    degenerated_pd: float
    fuel_power_curve: FuelPowerCurve | None

    @classmethod
    def from_raw_lists(
        cls,
        energy_usage_values: list[float],
        rate_values: list[float] | None = None,
        suction_pressure_values: list[float] | None = None,
        discharge_pressure_values: list[float] | None = None,
        power_interpolation_values: list[float] | None = None,
    ) -> SampledCompressorData:
        _validate_raw_lists(
            energy_usage_values,
            rate_values,
            suction_pressure_values,
            discharge_pressure_values,
            power_interpolation_values,
        )
        fuel_power_curve: FuelPowerCurve | None = None
        if power_interpolation_values is not None:
            fuel_values = _as_float_array(energy_usage_values)
            power_values_array = _as_float_array(power_interpolation_values)
            sorted_fuel, sorted_power = _require_strictly_monotonic_fuel_power_samples(fuel_values, power_values_array)
            fuel_power_curve = FuelPowerCurve(sorted_fuel=sorted_fuel, sorted_power=sorted_power)
        provided_variables: dict[VariableName, FloatArray] = {
            name: _as_float_array(values)
            for name, values in cast(
                "tuple[tuple[VariableName, list[float] | None], ...]",
                (
                    (RATE_NAME, rate_values),
                    (PS_NAME, suction_pressure_values),
                    (PD_NAME, discharge_pressure_values),
                ),
            )
            if values is not None
        }
        required_variables: list[VariableName] = list(provided_variables)
        active_variables = _determine_active_variables(provided_variables)
        if not active_variables:
            raise IllegalStateException("At least one variable must be non-degenerate.")
        degenerated_rate = (
            float(provided_variables[RATE_NAME][0])
            if RATE_NAME in required_variables and RATE_NAME not in active_variables
            else np.inf
        )
        degenerated_ps = (
            float(provided_variables[PS_NAME][0])
            if PS_NAME in required_variables and PS_NAME not in active_variables
            else -np.inf
        )
        degenerated_pd = (
            float(provided_variables[PD_NAME][0])
            if PD_NAME in required_variables and PD_NAME not in active_variables
            else np.inf
        )
        return cls(
            energy_usage_values=energy_usage_values,
            rate_values=rate_values,
            suction_pressure_values=suction_pressure_values,
            discharge_pressure_values=discharge_pressure_values,
            power_interpolation_values=power_interpolation_values,
            provided_variables=provided_variables,
            required_variables=required_variables,
            active_variables=active_variables,
            degenerated_rate=degenerated_rate,
            degenerated_ps=degenerated_ps,
            degenerated_pd=degenerated_pd,
            fuel_power_curve=fuel_power_curve,
        )


__all__ = [
    "PD_NAME",
    "PS_NAME",
    "RATE_NAME",
    "SampledCompressorData",
    "VariableName",
]
