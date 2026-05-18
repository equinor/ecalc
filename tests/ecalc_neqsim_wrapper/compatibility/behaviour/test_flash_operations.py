"""PH/TP flash behaviour checks used by compressor workflows."""

from __future__ import annotations

import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS, is_state_supported
from ..envelope import EOS_MODELS

_GAS_DOMINANT_COMPOSITIONS = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "rich_associated_gas",
    "co2_heavy_injection",
    "n2_heavy",
)


def _assert_clean_state(fluid: NeqsimFluid, context: str) -> None:
    for prop in ("density", "z", "kappa", "enthalpy_joule_per_kg", "vapor_fraction_molar"):
        value = getattr(fluid, prop)
        assert math.isfinite(value), f"non-finite {prop} {context}: {value!r}"
    assert fluid.density > 0.0, f"non-positive density {context}: {fluid.density!r}"
    assert abs(fluid.kappa - 1.0) > 1.0e-6, f"default kappa {context}: {fluid.kappa!r}"


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_ph_flash_produces_fluid_with_requested_enthalpy(composition_name):
    """set_new_pressure_and_enthalpy(P, h) returns a fluid whose
    enthalpy matches h. This is the load-bearing invariant for the
    compressor head -> outlet temperature derivation in ecalc."""
    composition = COMPOSITIONS[composition_name]
    inlet = NeqsimFluid.create_thermo_system(composition=composition, pressure_bara=20.0, temperature_kelvin=313.0)
    # Realistic single-stage compressor head.
    target_enthalpy = inlet.enthalpy_joule_per_kg + 80_000.0
    result = inlet.set_new_pressure_and_enthalpy(new_pressure=60.0, new_enthalpy_joule_per_kg=target_enthalpy)

    achieved = result.enthalpy_joule_per_kg
    error = abs(achieved - target_enthalpy)
    # PH flash is iterative; allow a small solver residual.
    assert error < 1.0e1, (
        f"PH flash did not converge to requested enthalpy on {composition_name}: "
        f"target={target_enthalpy!r} J/kg achieved={achieved!r} J/kg error={error:.2e} J/kg"
    )


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_ph_flash_enthalpy_increase_raises_temperature(composition_name):
    """Adding enthalpy at fixed pressure must raise temperature; removing
    it must lower temperature. Catches sign errors in PH wiring."""
    composition = COMPOSITIONS[composition_name]
    inlet = NeqsimFluid.create_thermo_system(composition=composition, pressure_bara=50.0, temperature_kelvin=320.0)
    base_enthalpy = inlet.enthalpy_joule_per_kg
    base_temperature = inlet.temperature_kelvin

    hotter = inlet.set_new_pressure_and_enthalpy(new_pressure=50.0, new_enthalpy_joule_per_kg=base_enthalpy + 50_000.0)
    cooler = inlet.set_new_pressure_and_enthalpy(new_pressure=50.0, new_enthalpy_joule_per_kg=base_enthalpy - 50_000.0)

    assert hotter.temperature_kelvin > base_temperature + 5.0, (
        f"adding 50 kJ/kg of enthalpy did not raise T meaningfully on {composition_name}: "
        f"base={base_temperature!r} K hotter={hotter.temperature_kelvin!r} K"
    )
    assert cooler.temperature_kelvin < base_temperature - 5.0, (
        f"removing 50 kJ/kg of enthalpy did not lower T meaningfully on {composition_name}: "
        f"base={base_temperature!r} K cooler={cooler.temperature_kelvin!r} K"
    )


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_tp_flash_and_ph_flash_are_consistent(composition_name):
    """A TP flash followed by a PH flash targeting the same enthalpy must
    recover the original temperature. This cross-checks that the two flash
    paths agree on the thermodynamic state."""
    composition = COMPOSITIONS[composition_name]
    inlet = NeqsimFluid.create_thermo_system(composition=composition, pressure_bara=50.0, temperature_kelvin=320.0)
    recovered = inlet.set_new_pressure_and_enthalpy(
        new_pressure=50.0,
        new_enthalpy_joule_per_kg=inlet.enthalpy_joule_per_kg,
    )
    error = abs(recovered.temperature_kelvin - inlet.temperature_kelvin)
    assert error < 0.5, (
        f"TP→PH round-trip temperature error on {composition_name}: "
        f"original={inlet.temperature_kelvin!r} K recovered={recovered.temperature_kelvin!r} K"
    )


# Five intercooled stages, matching segmented compressor pipelines.
_COMPRESSION_PRESSURES_BARA = (5.0, 15.0, 40.0, 90.0, 200.0)
_INTERSTAGE_TEMPERATURE_KELVIN = 313.0


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_sequential_compression_chain_keeps_properties_well_defined(composition_name):
    """A five-stage interstage-cooled compression must produce a clean
    pipeline: every intermediate fluid has finite, non-default
    properties; density rises monotonically with pressure."""
    composition = COMPOSITIONS[composition_name]
    fluid = NeqsimFluid.create_thermo_system(
        composition=composition,
        pressure_bara=_COMPRESSION_PRESSURES_BARA[0],
        temperature_kelvin=_INTERSTAGE_TEMPERATURE_KELVIN,
    )
    densities = [fluid.density]
    for pressure in _COMPRESSION_PRESSURES_BARA[1:]:
        fluid = fluid.set_new_pressure_and_temperature(pressure, _INTERSTAGE_TEMPERATURE_KELVIN)
        for prop in ("density", "z", "kappa", "enthalpy_joule_per_kg"):
            value = getattr(fluid, prop)
            assert math.isfinite(value), f"non-finite {prop} after compression to {pressure} bara on {composition_name}"
        assert abs(fluid.kappa - 1.0) > 1.0e-6, (
            f"default kappa at {pressure} bara on {composition_name}: {fluid.kappa!r}"
        )
        densities.append(fluid.density)

    for previous, current, pressure in zip(densities, densities[1:], _COMPRESSION_PRESSURES_BARA[1:]):
        assert current > previous, (
            f"density not monotonic in pressure during compression chain on "
            f"{composition_name}: at P={pressure} bara density={current!r} <= "
            f"previous stage density={previous!r}"
        )


_PH_PROBE_CASES = [
    pytest.param(
        composition_name,
        pressure_bara,
        temperature_kelvin,
        eos_model,
        30_000.0,
        id=f"{composition_name}-P{pressure_bara:g}bara-T{temperature_kelvin:g}K-{eos_model.name}-near-envelope",
    )
    for composition_name, pressure_bara, temperature_kelvin in (
        ("c3_rich_wellstream_dry", 90.0, 305.0),
        ("rich_associated_gas", 70.0, 290.0),
        ("typical_export_gas", 80.0, 280.0),
        ("co2_heavy_injection", 60.0, 290.0),
        ("lean_natural_gas", 50.0, 270.0),
    )
    for eos_model in EOS_MODELS
] + [
    pytest.param(
        composition_name,
        pressure_bara,
        temperature_kelvin,
        eos_model,
        50_000.0,
        id=f"{composition_name}-P{pressure_bara:g}bara-T{temperature_kelvin:g}K-{eos_model.name}-max-speed-probe",
    )
    for composition_name in COMPOSITIONS
    for pressure_bara, temperature_kelvin in [(500.0, 400.0), (500.0, 450.0), (2000.0, 400.0), (2000.0, 450.0)]
    if is_state_supported(composition_name, temperature_kelvin)
    for eos_model in EOS_MODELS
]


@pytest.mark.parametrize(
    "composition_name,pressure_bara,temperature_kelvin,eos_model,enthalpy_delta",
    _PH_PROBE_CASES,
)
def test_ph_flash_at_probe_conditions_returns_finite_state(
    composition_name, pressure_bara, temperature_kelvin, eos_model, enthalpy_delta
):
    composition = COMPOSITIONS[composition_name]
    inlet = NeqsimFluid.create_thermo_system(
        composition=composition,
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        eos_model=eos_model,
    )
    _assert_clean_state(
        inlet, f"on inlet {composition_name} ({eos_model.name}) at {pressure_bara} bara, {temperature_kelvin} K"
    )

    result = inlet.set_new_pressure_and_enthalpy(
        new_pressure=pressure_bara,
        new_enthalpy_joule_per_kg=inlet.enthalpy_joule_per_kg + enthalpy_delta,
    )
    _assert_clean_state(
        result,
        f"after PH flash on {composition_name} ({eos_model.name}) at {pressure_bara} bara, {temperature_kelvin} K",
    )
