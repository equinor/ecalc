"""External-reference checks against ideal-gas and pure-methane anchors."""

from __future__ import annotations

import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.fluid_model import FluidComposition

from ..compositions import COMPOSITIONS
from ..envelope import EOS_MODELS

R_J_PER_MOL_K = ThermodynamicConstants.R_J_PER_MOL_K

# Low enough for ideal-gas behaviour, high enough to avoid numerical edges.
IDEAL_LIMIT_PRESSURE_BARA = 0.01

# Representative compositions for the ideal-gas-limit wiring check.
_IDEAL_LIMIT_COMPOSITIONS = (
    "pure_methane",
    "typical_export_gas",
    "co2_heavy_injection",
    "c3_rich_wellstream_dry",
)

# Cold and warm envelope ends.
IDEAL_LIMIT_TEMPERATURES_KELVIN = (280.0, 380.0)


def _ideal_gas_density(pressure_bara: float, temperature_kelvin: float, molar_mass_kg_per_mol: float) -> float:
    """Return ρ = P·M / (R·T) in kg/m³ for the given state."""
    pressure_pa = pressure_bara * 1.0e5
    return pressure_pa * molar_mass_kg_per_mol / (R_J_PER_MOL_K * temperature_kelvin)


_IDEAL_LIMIT_CASES = [
    pytest.param(
        name,
        temperature_kelvin,
        eos_model,
        id=f"{name}-T{temperature_kelvin:g}K-{eos_model.name}",
    )
    for name in _IDEAL_LIMIT_COMPOSITIONS
    for temperature_kelvin in IDEAL_LIMIT_TEMPERATURES_KELVIN
    for eos_model in EOS_MODELS
]


@pytest.mark.parametrize("composition_name,temperature_kelvin,eos_model", _IDEAL_LIMIT_CASES)
def test_ideal_gas_limit(composition_name, temperature_kelvin, eos_model):
    """Both Z → 1 and ρ → ideal-gas reference at 0.01 bara.

    At very low pressure every real gas converges on the ideal-gas law.
    Any divergence here points at the EoS, the unit conversion, or the
    property wiring.
    """
    composition = COMPOSITIONS[composition_name]
    fluid = NeqsimFluid.create_thermo_system(
        composition=composition,
        pressure_bara=IDEAL_LIMIT_PRESSURE_BARA,
        temperature_kelvin=temperature_kelvin,
        eos_model=eos_model,
    )

    z = fluid.z
    assert math.isfinite(z), (
        f"non-finite Z at {composition_name} {eos_model.name} P={IDEAL_LIMIT_PRESSURE_BARA} T={temperature_kelvin}"
    )
    assert abs(z - 1.0) < 1.0e-3, (
        f"Z={z!r} deviates from ideal-gas limit by more than 0.1 % "
        f"at {composition_name} {eos_model.name} "
        f"P={IDEAL_LIMIT_PRESSURE_BARA} bara T={temperature_kelvin} K"
    )

    expected_density = _ideal_gas_density(
        pressure_bara=IDEAL_LIMIT_PRESSURE_BARA,
        temperature_kelvin=temperature_kelvin,
        molar_mass_kg_per_mol=composition.molar_mass_mixture,
    )
    actual_density = fluid.density
    assert math.isfinite(actual_density), (
        f"non-finite density at {composition_name} {eos_model.name} "
        f"P={IDEAL_LIMIT_PRESSURE_BARA} T={temperature_kelvin}"
    )
    relative_error = abs(actual_density - expected_density) / expected_density
    assert relative_error < 1.0e-3, (
        f"density={actual_density!r} kg/m3 deviates from ideal-gas reference "
        f"{expected_density!r} kg/m3 by {relative_error:.3%} at "
        f"{composition_name} {eos_model.name} "
        f"P={IDEAL_LIMIT_PRESSURE_BARA} bara T={temperature_kelvin} K"
    )


_PURE_CH4 = FluidComposition(methane=100.0).normalized()

# NIST WebBook methane anchors: (T [K], P [bara], ρ [kg/m³], Z).
_PURE_METHANE_ANCHORS = (
    (300.0, 1.0, 0.6435, 0.998),
    (300.0, 10.0, 6.514, 0.987),
)


@pytest.mark.parametrize(
    "temperature_kelvin,pressure_bara,density_reference,z_reference",
    _PURE_METHANE_ANCHORS,
    ids=[f"T{t:g}K-P{p:g}bara" for t, p, _, _ in _PURE_METHANE_ANCHORS],
)
def test_pure_methane_density_matches_nist(temperature_kelvin, pressure_bara, density_reference, z_reference):
    """Pure-methane density at low-to-moderate P agrees with NIST WebBook
    (Setzmann–Wagner reference EoS). A 0.5 % tolerance accommodates the
    gap between the reference equation and the cubic EoS NeqSim uses."""
    fluid = NeqsimFluid.create_thermo_system(
        composition=_PURE_CH4,
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
    )
    actual_density = fluid.density
    actual_z = fluid.z
    density_relative_error = abs(actual_density - density_reference) / density_reference
    z_relative_error = abs(actual_z - z_reference) / z_reference
    assert density_relative_error < 5.0e-3, (
        f"pure-CH4 density={actual_density!r} kg/m³ vs NIST {density_reference} "
        f"deviates by {density_relative_error:.3%} at "
        f"P={pressure_bara} bara T={temperature_kelvin} K"
    )
    assert z_relative_error < 5.0e-3, (
        f"pure-CH4 Z={actual_z!r} vs NIST {z_reference} deviates by "
        f"{z_relative_error:.3%} at P={pressure_bara} bara T={temperature_kelvin} K"
    )
