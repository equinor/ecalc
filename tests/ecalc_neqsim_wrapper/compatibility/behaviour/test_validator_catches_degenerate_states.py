"""Probe-edge states must fail in NeqSim or be rejected by validators."""

import math

import pytest

from ecalc_neqsim_wrapper.exceptions import JAVA_ERRORS, NeqsimFlashCalculationError
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.process.fluid_stream.fluid_properties import FluidProperties
from libecalc.process.fluid_stream.fluid_property_validation import (
    require_positive_finite,
    validate_ph_flash_result,
)

from ..compositions import COMPOSITIONS

_ACCEPTED_NEQSIM_ERRORS = (NeqsimFlashCalculationError, *JAVA_ERRORS)


# Degraded-output shape check; broad composition coverage lives elsewhere.
_PROBE_COMPOSITIONS = ("pure_methane", "typical_export_gas")


def _snapshot(fluid: NeqsimFluid) -> FluidProperties:
    """Read the wrapper's thermodynamic properties into the dataclass the
    validator consumes.

    ``standard_density`` is not a state property of ``NeqsimFluid`` (it
    lives on the higher-level wrapper). A finite positive placeholder is
    fine here: we want the validator to trip on the degraded *state*
    fields (pressure, T, density, Z, kappa, vapor fraction, enthalpy),
    not on the standard-density slot.
    """
    return FluidProperties(
        temperature_kelvin=fluid.temperature_kelvin,
        pressure_bara=fluid.pressure_bara,
        density=fluid.density,
        enthalpy_joule_per_kg=fluid.enthalpy_joule_per_kg,
        z=fluid.z,
        kappa=fluid.kappa,
        vapor_fraction_molar=fluid.vapor_fraction_molar,
        molar_mass=fluid.molar_mass,
        standard_density=1.0,
    )


@pytest.mark.parametrize(
    "target_enthalpy_joule_per_kg",
    [1.0e15, -1.0e15],
    ids=["high", "low"],
)
@pytest.mark.parametrize("composition_name", _PROBE_COMPOSITIONS)
def test_validator_rejects_unreachable_enthalpy_ph_flash(composition_name, target_enthalpy_joule_per_kg):
    """A PH flash targeting an enthalpy far outside the physically reachable
    range at the given pressure either raises in NeqSim or returns a state
    the ecalc validator rejects. Covers both the pathologically high and
    pathologically low targets."""
    fluid = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=50.0,
        temperature_kelvin=300.0,
    )

    try:
        flashed = fluid.set_new_pressure_and_enthalpy(
            new_pressure=50.0,
            new_enthalpy_joule_per_kg=target_enthalpy_joule_per_kg,
        )
    except _ACCEPTED_NEQSIM_ERRORS:
        return

    with pytest.raises(ValueError):
        validate_ph_flash_result(
            _snapshot(flashed),
            target_enthalpy_joule_per_kg=target_enthalpy_joule_per_kg,
            context="compatibility: unreachable enthalpy",
        )


@pytest.mark.parametrize("composition_name", _PROBE_COMPOSITIONS)
def test_validator_rejects_non_positive_pressure_state(composition_name):
    """A non-physical negative-pressure state either fails to construct
    in NeqSim or yields properties that the ecalc validator rejects via
    ``require_positive_finite``. Pins that the detection signal exists."""
    try:
        fluid = NeqsimFluid.create_thermo_system(
            composition=COMPOSITIONS[composition_name],
            pressure_bara=-10.0,
            temperature_kelvin=300.0,
        )
    except _ACCEPTED_NEQSIM_ERRORS:
        return

    snapshot = _snapshot(fluid)
    bad_property_caught = False
    for name, value in (
        ("pressure_bara", snapshot.pressure_bara),
        ("density", snapshot.density),
        ("z", snapshot.z),
        ("kappa", snapshot.kappa),
    ):
        try:
            require_positive_finite(value, name, "compatibility: negative pressure")
        except ValueError:
            bad_property_caught = True
            break
        else:
            if not math.isfinite(value):
                bad_property_caught = True
                break

    assert bad_property_caught, (
        f"Non-physical state at -10 bara produced an output the validator did not catch: "
        f"P={snapshot.pressure_bara}, rho={snapshot.density}, "
        f"Z={snapshot.z}, kappa={snapshot.kappa}. "
        f"NeqSim's degraded-output shape changed: the validator must be updated "
        f"so the compressor probe can still detect 'not workable'."
    )
