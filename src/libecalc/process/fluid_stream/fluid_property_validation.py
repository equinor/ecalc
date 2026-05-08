from __future__ import annotations

import math
from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_properties import FluidProperties

PH_ENTHALPY_REL_TOLERANCE = 1e-4
PH_ENTHALPY_ABS_TOLERANCE_JOULE_PER_KG = 10.0
VAPOR_FRACTION_TOLERANCE = 1e-5
# Defensive PH-result validation tolerances. These are not process-model tolerances.
# They only guard against thermodynamic backend failures where a PH flash returns
# an unusable or wrong target state instead of raising. The absolute tolerance
# covers low-enthalpy states; the relative tolerance scales with compressor
# enthalpy levels.


def _default_error_factory(message: str) -> ValueError:
    return ValueError(message)


def require_positive_finite(
    value: float,
    name: str,
    context: str,
    error_factory: Callable[[str], Exception] = _default_error_factory,
) -> None:
    if not math.isfinite(value) or value <= 0:
        raise error_factory(f"{context}: expected finite positive {name}, got {value}.")


def validate_ph_flash_result(
    properties: FluidProperties,
    target_enthalpy_joule_per_kg: float,
    context: str,
    error_factory: Callable[[str], Exception] = _default_error_factory,
) -> None:
    """Validate a PH flash result against the caller's target enthalpy.

    This is intentionally not a ``FluidProperties`` invariant: the enthalpy
    target and acceptable tolerance belong to the flash operation, not to a raw
    immutable fluid-state snapshot.
    """
    require_positive_finite(properties.pressure_bara, "pressure_bara", context, error_factory)
    require_positive_finite(properties.temperature_kelvin, "temperature_kelvin", context, error_factory)
    require_positive_finite(properties.density, "density", context, error_factory)
    require_positive_finite(properties.z, "z", context, error_factory)
    require_positive_finite(properties.kappa, "kappa", context, error_factory)
    require_positive_finite(properties.standard_density, "standard_density", context, error_factory)

    if (
        not math.isfinite(properties.vapor_fraction_molar)
        or not -VAPOR_FRACTION_TOLERANCE <= properties.vapor_fraction_molar <= 1 + VAPOR_FRACTION_TOLERANCE
    ):
        raise error_factory(
            f"{context}: expected finite vapor_fraction_molar in [0, 1], got {properties.vapor_fraction_molar}."
        )

    if not math.isfinite(properties.enthalpy_joule_per_kg):
        raise error_factory(
            f"{context}: expected finite enthalpy_joule_per_kg, got {properties.enthalpy_joule_per_kg}."
        )
    if not math.isfinite(target_enthalpy_joule_per_kg):
        raise error_factory(
            f"{context}: expected finite target_enthalpy_joule_per_kg, got {target_enthalpy_joule_per_kg}."
        )

    enthalpy_error = abs(properties.enthalpy_joule_per_kg - target_enthalpy_joule_per_kg)
    enthalpy_tolerance = max(
        PH_ENTHALPY_ABS_TOLERANCE_JOULE_PER_KG,
        abs(target_enthalpy_joule_per_kg) * PH_ENTHALPY_REL_TOLERANCE,
    )
    if enthalpy_error > enthalpy_tolerance:
        raise error_factory(
            f"{context}: PH flash did not satisfy target enthalpy. "
            f"target={target_enthalpy_joule_per_kg}, result={properties.enthalpy_joule_per_kg}, "
            f"error={enthalpy_error}, tolerance={enthalpy_tolerance}."
        )
