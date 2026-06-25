"""Finite-property and physical-bound checks across the envelope."""

import math
from dataclasses import dataclass

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.process.fluid_stream.fluid_model import EoSModel

from ..compositions import COMPOSITIONS, is_state_supported
from ..envelope import EOS_MODELS, high_pressure_grid


def _case_id(name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> str:
    return f"{name}-P{pressure_bara:g}bara-T{temperature_kelvin:g}K-{eos_model.name}"


@dataclass(frozen=True)
class _Bounds:
    kappa_hi: float
    z_hi: float
    kappa_lo: float = 1.02
    z_lo: float = 0.05


_NOMINAL_BOUNDS = _Bounds(kappa_hi=2.0, z_hi=2.5)
_ELEVATED_BOUNDS = _Bounds(kappa_hi=5.0, z_hi=4.0)

# Low/mid/high pressure × cold/mid/warm temperature.
_SANITY_NOMINAL_GRID: list[tuple[float, float]] = [(p, t) for p in (5.0, 50.0, 200.0) for t in (250.0, 300.0, 380.0)]

# Max-speed-probe corners.
_SANITY_MAX_SPEED_PROBE_GRID: list[tuple[float, float]] = [(p, t) for p in (500.0, 2000.0) for t in (400.0, 450.0)]


def _build_cases(grid, bounds: _Bounds):
    return [
        pytest.param(
            name,
            composition,
            pressure_bara,
            temperature_kelvin,
            eos_model,
            bounds,
            id=_case_id(name, pressure_bara, temperature_kelvin, eos_model),
        )
        for name, composition in COMPOSITIONS.items()
        for pressure_bara, temperature_kelvin in grid
        if is_state_supported(name, temperature_kelvin)
        for eos_model in EOS_MODELS
    ]


_ALL_CASES = (
    _build_cases(_SANITY_NOMINAL_GRID, _NOMINAL_BOUNDS)
    + _build_cases(high_pressure_grid(), _ELEVATED_BOUNDS)
    + _build_cases(_SANITY_MAX_SPEED_PROBE_GRID, _ELEVATED_BOUNDS)
)


@pytest.fixture(scope="module")
def fluid_factory():
    """Build NeqsimFluid instances; cached per (name, P, T, EoS) within the module run."""
    cache: dict[tuple[str, float, float, EoSModel], NeqsimFluid] = {}

    def factory(name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> NeqsimFluid:
        key = (name, pressure_bara, temperature_kelvin, eos_model)
        if key not in cache:
            cache[key] = NeqsimFluid.create_thermo_system(
                composition=COMPOSITIONS[name],
                pressure_bara=pressure_bara,
                temperature_kelvin=temperature_kelvin,
                eos_model=eos_model,
            )
        return cache[key]

    return factory


@pytest.mark.parametrize("name,composition,pressure_bara,temperature_kelvin,eos_model,bounds", _ALL_CASES)
def test_all_properties_finite(name, composition, pressure_bara, temperature_kelvin, eos_model, bounds, fluid_factory):
    """Every property ecalc reads from NeqSim must be finite at every envelope state."""
    fluid = fluid_factory(name, pressure_bara, temperature_kelvin, eos_model)
    for prop_name in ("density", "molar_mass", "z", "enthalpy_joule_per_kg", "kappa", "vapor_fraction_molar"):
        value = getattr(fluid, prop_name)
        assert math.isfinite(value), f"{prop_name} is not finite: {value!r}"


@pytest.mark.parametrize("name,composition,pressure_bara,temperature_kelvin,eos_model,bounds", _ALL_CASES)
def test_physical_bounds(name, composition, pressure_bara, temperature_kelvin, eos_model, bounds, fluid_factory):
    """Properties must sit within physically plausible ranges for a hydrocarbon mixture.

    Kappa and Z bounds are relaxed for the elevated-pressure regimes where
    dense-gas / supercritical roots produce higher values. The kappa lower
    bound of 1.02 subsumes the default-value check: NeqSim's uninitialised
    kappa is exactly 1.0 and would fail this bound.
    """
    fluid = fluid_factory(name, pressure_bara, temperature_kelvin, eos_model)
    assert bounds.kappa_lo < fluid.kappa < bounds.kappa_hi, (
        f"kappa={fluid.kappa!r} outside [{bounds.kappa_lo}, {bounds.kappa_hi})"
    )
    assert bounds.z_lo < fluid.z < bounds.z_hi, f"z={fluid.z!r} outside ({bounds.z_lo}, {bounds.z_hi})"
    assert 0.0 < fluid.density < 1500.0, f"density={fluid.density!r}"
    assert 0.0 <= fluid.vapor_fraction_molar <= 1.0, f"vapor_fraction_molar={fluid.vapor_fraction_molar!r}"
    assert -5e6 < fluid.enthalpy_joule_per_kg < 5e6, (
        f"enthalpy_joule_per_kg={fluid.enthalpy_joule_per_kg!r} outside plausible band"
    )
