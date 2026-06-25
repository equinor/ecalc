"""State identity and copy-independence checks."""

import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS

_GAS_DOMINANT_COMPOSITIONS = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "rich_associated_gas",
    "co2_heavy_injection",
    "n2_heavy",
)


@pytest.mark.parametrize("composition_name", list(COMPOSITIONS))
def test_composition_round_trip(composition_name):
    """The composition reported by `fluid.composition` must reproduce
    the input composition. A change to the NeqSim-to-ecalc name
    mapping would silently corrupt every downstream composition-aware
    calculation; this test pins the round-trip.
    """
    composition = COMPOSITIONS[composition_name].normalized()
    fluid = NeqsimFluid.create_thermo_system(
        composition=composition,
        pressure_bara=20.0,
        temperature_kelvin=300.0,
    )
    recovered = fluid.composition.normalized()

    original = vars(composition)
    recovered_dict = vars(recovered)
    for component, original_fraction in original.items():
        recovered_fraction = recovered_dict[component]
        assert abs(recovered_fraction - original_fraction) < 1.0e-12, (
            f"component {component} drifted in composition round-trip on "
            f"{composition_name}: original={original_fraction!r} "
            f"recovered={recovered_fraction!r}"
        )


@pytest.mark.parametrize("composition_name", list(COMPOSITIONS))
def test_re_flash_at_same_state_is_idempotent(composition_name):
    """Flashing a system back to its own (P, T) must not shift properties.

    `set_new_pressure_and_temperature(P, T)` against the current (P, T)
    should be a no-op for properties. Any non-trivial change indicates
    caching-vs-recompute confusion in the wrapper or the underlying
    flash routine.
    """
    fluid = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=30.0,
        temperature_kelvin=320.0,
    )
    reflashed = fluid.set_new_pressure_and_temperature(fluid.pressure_bara, fluid.temperature_kelvin)
    for prop in ("density", "z", "kappa", "molar_mass", "enthalpy_joule_per_kg"):
        original = getattr(fluid, prop)
        re_value = getattr(reflashed, prop)
        denom = max(abs(original), 1.0)
        relative_error = abs(original - re_value) / denom
        assert relative_error < 1.0e-12, (
            f"{prop} drifted after re-flashing at the same state on "
            f"{composition_name}: original={original!r} reflashed={re_value!r} "
            f"rel_err={relative_error:.2e}"
        )


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_tp_flash_round_trip_returns_to_initial_state(composition_name):
    """create(P0, T0) -> setPT(P1, T1) -> setPT(P0, T0) recovers the start.

    Real EoS calculations are reversible in T and P (no path dependence
    for single-phase gases). The round-trip checks that no internal
    state leaks across flashes and that property getters are pure.
    """
    composition = COMPOSITIONS[composition_name]
    p0, t0 = 30.0, 313.0
    p1, t1 = 120.0, 360.0

    direct = NeqsimFluid.create_thermo_system(composition=composition, pressure_bara=p0, temperature_kelvin=t0)
    intermediate = direct.set_new_pressure_and_temperature(p1, t1)
    round_tripped = intermediate.set_new_pressure_and_temperature(p0, t0)

    for prop in ("density", "z", "kappa", "molar_mass", "enthalpy_joule_per_kg"):
        direct_value = getattr(direct, prop)
        round_value = getattr(round_tripped, prop)
        denom = max(abs(direct_value), 1.0)
        relative_error = abs(direct_value - round_value) / denom
        assert relative_error < 1.0e-9, (
            f"{prop} drifted after TP round-trip on {composition_name}: "
            f"direct={direct_value!r} round-tripped={round_value!r} "
            f"rel_err={relative_error:.2e}"
        )


def test_copy_produces_independent_instance():
    """Two copies of the same fluid must be independent: mutating one
    through `set_new_pressure_and_temperature` must not affect the
    other's properties. Returned `set_new_*` methods do build new
    instances, but the underlying Java system is cloned inside
    `.copy()` -- this test guards the clone-on-copy behaviour."""
    base = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS["lean_natural_gas"],
        pressure_bara=20.0,
        temperature_kelvin=300.0,
    )
    other = base.copy()
    original_base_density = base.density
    original_other_density = other.density

    moved = other.set_new_pressure_and_temperature(120.0, 360.0)
    assert moved.density != original_other_density

    assert math.isclose(base.density, original_base_density, rel_tol=1.0e-12), (
        f"base density changed after mutating a copy: before={original_base_density!r} after={base.density!r}"
    )
    assert math.isclose(other.density, original_other_density, rel_tol=1.0e-12), (
        f"original copy density changed after a derived setter was called: "
        f"before={original_other_density!r} after={other.density!r}"
    )
