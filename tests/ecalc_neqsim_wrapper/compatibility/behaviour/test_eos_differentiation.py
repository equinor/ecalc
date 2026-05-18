"""EoS routing checks: SRK/PR differ, GERG setters refresh properties."""

from __future__ import annotations

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.process.fluid_stream.fluid_model import EoSModel

from ..compositions import COMPOSITIONS

_GAS_DOMINANT_COMPOSITIONS = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "rich_associated_gas",
    "co2_heavy_injection",
    "n2_heavy",
)


@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_srk_and_pr_produce_measurably_different_densities(composition_name):
    """SRK and PR are different cubic equations of state. At moderate
    pressure they must produce measurably different (but close)
    densities. Bit-identical output would mean the EoS selector is
    wired wrong."""
    pressure_bara = 100.0
    temperature_kelvin = 320.0
    srk = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        eos_model=EoSModel.SRK,
    )
    pr = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        eos_model=EoSModel.PR,
    )
    density_diff = abs(srk.density - pr.density) / srk.density
    assert density_diff > 1.0e-4, (
        f"SRK and PR densities are suspiciously close for {composition_name}: "
        f"srk={srk.density!r} pr={pr.density!r} rel_diff={density_diff:.2e}"
    )
    assert density_diff < 0.10, (
        f"SRK and PR densities differ by more than 10 % for {composition_name}: "
        f"srk={srk.density!r} pr={pr.density!r} rel_diff={density_diff:.2%}"
    )
    kappa_diff = abs(srk.kappa - pr.kappa) / srk.kappa
    assert kappa_diff > 1.0e-4, (
        f"SRK and PR kappa are suspiciously close for {composition_name}: "
        f"srk={srk.kappa!r} pr={pr.kappa!r} rel_diff={kappa_diff:.2e}"
    )
    z_diff = abs(srk.z - pr.z) / srk.z
    assert z_diff > 1.0e-4, (
        f"SRK and PR Z are suspiciously close for {composition_name}: srk={srk.z!r} pr={pr.z!r} rel_diff={z_diff:.2e}"
    )


@pytest.mark.parametrize("eos_model", (EoSModel.GERG_SRK, EoSModel.GERG_PR))
@pytest.mark.parametrize("composition_name", _GAS_DOMINANT_COMPOSITIONS)
def test_gerg_properties_refresh_after_setting_new_state(composition_name, eos_model):
    """Under the GERG code path, properties cached at construction time
    must reflect the new state after a TP setter — not the original
    construction state."""
    state_a_p, state_a_t = 20.0, 310.0
    state_b_p, state_b_t = 80.0, 350.0

    direct_state_b = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=state_b_p,
        temperature_kelvin=state_b_t,
        eos_model=eos_model,
    )
    via_setter = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=state_a_p,
        temperature_kelvin=state_a_t,
        eos_model=eos_model,
    ).set_new_pressure_and_temperature(state_b_p, state_b_t)

    for prop in ("density", "z", "kappa", "enthalpy_joule_per_kg"):
        direct_value = getattr(direct_state_b, prop)
        setter_value = getattr(via_setter, prop)
        denom = max(abs(direct_value), 1.0)
        relative_error = abs(direct_value - setter_value) / denom
        assert relative_error < 1.0e-6, (
            f"{eos_model.name} cache appears stale: {prop} via setter "
            f"({setter_value!r}) does not match direct construction "
            f"at the same state ({direct_value!r}) for {composition_name}; "
            f"rel_err={relative_error:.2e}"
        )
