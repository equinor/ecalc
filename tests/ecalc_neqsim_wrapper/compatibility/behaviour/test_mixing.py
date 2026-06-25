"""Molar-balance check for `mix_neqsim_streams`."""

import math

from ecalc_neqsim_wrapper.thermo import mix_neqsim_streams

from ..compositions import COMPOSITIONS


def test_mixing_two_different_streams_obeys_molar_balance():
    """Mixing two streams of differing composition must produce a
    composition equal to the molar-weighted average of the inputs.

    The reference is computed analytically from the input compositions
    and their molar flow rates, with no NeqSim involvement."""
    composition_1 = COMPOSITIONS["lean_natural_gas"]
    composition_2 = COMPOSITIONS["rich_associated_gas"]
    mass_rate_1 = 30_000.0
    mass_rate_2 = 10_000.0

    pressure_bara = 40.0
    temperature_kelvin = 315.0
    mixed_composition, mixed_fluid = mix_neqsim_streams(
        stream_composition_1=composition_1,
        stream_composition_2=composition_2,
        mass_rate_stream_1=mass_rate_1,
        mass_rate_stream_2=mass_rate_2,
        pressure=pressure_bara,
        temperature=temperature_kelvin,
    )

    # Analytic reference: mass flows -> molar flows -> mole fractions.
    molar_flow_1 = mass_rate_1 / composition_1.molar_mass_mixture
    molar_flow_2 = mass_rate_2 / composition_2.molar_mass_mixture

    components_1 = vars(composition_1.normalized())
    components_2 = vars(composition_2.normalized())
    expected_mole_amount: dict[str, float] = {}
    for component in components_1.keys() | components_2.keys():
        expected_mole_amount[component] = (
            components_1.get(component, 0.0) * molar_flow_1 + components_2.get(component, 0.0) * molar_flow_2
        )
    total = sum(expected_mole_amount.values())
    expected_fractions = {c: amount / total for c, amount in expected_mole_amount.items()}

    mixed_dict = vars(mixed_composition.normalized())
    for component, expected_fraction in expected_fractions.items():
        actual_fraction = mixed_dict[component]
        assert abs(actual_fraction - expected_fraction) < 1.0e-12, (
            f"mixed mole fraction for {component} drifted from molar balance: "
            f"expected={expected_fraction!r} actual={actual_fraction!r}"
        )

    assert math.isfinite(mixed_fluid.density) and mixed_fluid.density > 0.0
    assert math.isfinite(mixed_fluid.kappa)
    assert abs(mixed_fluid.kappa - 1.0) > 1.0e-6, "mixed fluid has default kappa"

    expected_mixed_molar_mass = (mass_rate_1 + mass_rate_2) / (molar_flow_1 + molar_flow_2)
    # NeqSim and FluidComposition use slightly different atomic weights.
    assert math.isclose(mixed_fluid.molar_mass, expected_mixed_molar_mass, rel_tol=1.0e-4), (
        f"mixed molar_mass={mixed_fluid.molar_mass!r} vs expected={expected_mixed_molar_mass!r}"
    )
