"""Gas-phase extraction and two-phase density checks."""

import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS


def _case_id(name: str, pressure_bara: float, temperature_kelvin: float) -> str:
    return f"{name}-P{pressure_bara:g}bara-T{temperature_kelvin:g}K"


_TWO_PHASE_POINTS_BARA_KELVIN: dict[str, tuple[tuple[float, float], ...]] = {
    "typical_export_gas": ((50.0, 280.0),),
    "rich_associated_gas": ((50.0, 280.0),),
    "c3_rich_wellstream": (
        (20.0, 280.0),
        (20.0, 300.0),
        (50.0, 280.0),
        (50.0, 300.0),
        (50.0, 330.0),
    ),
    "c3_rich_wellstream_dry": (
        (20.0, 280.0),
        (20.0, 300.0),
        (50.0, 280.0),
        (50.0, 300.0),
        (50.0, 330.0),
    ),
    "wet_lean_gas": (
        (20.0, 280.0),
        (50.0, 300.0),
        (100.0, 330.0),
    ),
}


_PHASE_EXTRACTION_CASES = [
    pytest.param(
        name,
        COMPOSITIONS[name],
        pressure_bara,
        temperature_kelvin,
        id=_case_id(name, pressure_bara, temperature_kelvin),
    )
    for name, points in _TWO_PHASE_POINTS_BARA_KELVIN.items()
    for pressure_bara, temperature_kelvin in points
]


@pytest.mark.parametrize("name,composition,pressure_bara,temperature_kelvin", _PHASE_EXTRACTION_CASES)
def test_clone_gas_phase_matches_clean_pt_flash(name, composition, pressure_bara, temperature_kelvin):
    """Extracting gas from a two-phase state matches a clean PT flash of
    the extracted gas-phase composition at the same (P, T)."""
    fluid = NeqsimFluid.create_thermo_system(
        composition=composition,
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
    )
    assert 1e-3 < fluid.vapor_fraction_molar < 0.999, (
        f"chosen probe state is not two-phase: vap_frac={fluid.vapor_fraction_molar!r}"
    )
    gas_only = fluid.clone_gas_phase()

    assert math.isclose(gas_only.vapor_fraction_molar, 1.0, rel_tol=1e-3)
    assert abs(gas_only.kappa - 1.0) > 1e-6, f"clone_gas_phase returned uninitialised-looking kappa={gas_only.kappa!r}"

    reference = NeqsimFluid.create_thermo_system(
        composition=gas_only.composition,
        pressure_bara=gas_only.pressure_bara,
        temperature_kelvin=gas_only.temperature_kelvin,
    )
    assert math.isclose(gas_only.kappa, reference.kappa, rel_tol=1e-3), (
        f"kappa drift: clone={gas_only.kappa!r} vs reference={reference.kappa!r}"
    )
    assert math.isclose(gas_only.z, reference.z, rel_tol=1e-3), (
        f"z drift: clone={gas_only.z!r} vs reference={reference.z!r}"
    )
    assert math.isclose(gas_only.density, reference.density, rel_tol=1e-3), (
        f"density drift: clone={gas_only.density!r} vs reference={reference.density!r}"
    )
    assert math.isclose(
        gas_only.enthalpy_joule_per_kg,
        reference.enthalpy_joule_per_kg,
        rel_tol=1e-3,
        # Tolerance for near-zero enthalpy reference values.
        abs_tol=10.0,
    ), f"enthalpy drift: clone={gas_only.enthalpy_joule_per_kg!r} vs reference={reference.enthalpy_joule_per_kg!r}"


def test_clone_gas_phase_on_single_phase_gas_is_stable():
    """Removing liquid from an already gas-only state is a stable no-op."""
    fluid = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS["pure_methane"],
        pressure_bara=20.0,
        temperature_kelvin=330.0,
    )
    assert fluid.vapor_fraction_molar > 0.999

    gas_only = fluid.clone_gas_phase()
    for prop in ("density", "z", "kappa", "molar_mass", "enthalpy_joule_per_kg"):
        original = getattr(fluid, prop)
        cloned = getattr(gas_only, prop)
        denom = max(abs(original), 1.0)
        relative_error = abs(original - cloned) / denom
        assert relative_error < 1.0e-9, (
            f"{prop} drifted after clone_gas_phase on single-phase gas: "
            f"original={original!r} gas_only={cloned!r} rel_err={relative_error:.2e}"
        )


def test_two_phase_bulk_density_lies_between_gas_and_liquid_extremes():
    """In a true two-phase state the bulk density should:

    * not equal the gas-only density (which is what `clone_gas_phase`
      would return), and
    * not exceed a reasonable liquid-density ceiling.

    Together these catch a silent failure where the wrapper returns
    the gas-only density on a two-phase mixture (which would be very
    wrong for any downstream mass-rate-aware calculation).
    """
    fluid = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS["c3_rich_wellstream"],
        pressure_bara=20.0,
        temperature_kelvin=270.0,
    )
    assert 0.01 < fluid.vapor_fraction_molar < 0.99, (
        f"chosen probe state is not two-phase: vap_frac={fluid.vapor_fraction_molar!r}"
    )
    bulk_density = fluid.density

    gas_only = fluid.clone_gas_phase()
    gas_density = gas_only.density

    relative_difference = abs(bulk_density - gas_density) / gas_density
    assert relative_difference > 1.0e-2, (
        f"two-phase bulk density ({bulk_density!r}) collapses to the "
        f"gas-only density ({gas_density!r}); rel_diff={relative_difference:.2e}"
    )
    # Even heavy hydrocarbon liquids stay below this ceiling.
    assert 0.0 < bulk_density < 1000.0, f"two-phase bulk density={bulk_density!r} outside plausible band"
