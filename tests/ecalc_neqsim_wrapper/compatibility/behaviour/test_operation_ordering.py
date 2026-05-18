"""Operation-ordering checks for the NeqSim wrapper.

Two distinct ordering questions:

1. **TP-flash transitions are state-function calls.** The result at
   ``(P2, T2)`` must not depend on which intermediate ``(P, T)`` path
   the wrapper took to get there, nor on whether ``(P2, T2)`` was
   reached via a fresh ``create_thermo_system`` or a flash from a
   different starting point. Mathematically obvious; numerically
   non-trivial. These tests pin the equivalence so a future NeqSim
   change that introduced path-dependence would surface here instead
   of as silent drift in compressor results.

2. **``clone_gas_phase`` does not commute with TP-flash.** Removing the
   liquid phase changes the system's mass and composition, so the
   order ``flash → remove`` produces a fundamentally different fluid
   from ``remove → flash``. The wrapper exposes both, and ecalc's
   compressor code relies on the rule "remove liquid at the operating
   point you care about". These tests *characterise* the difference
   (asserting it exists and is non-trivial) and pin the idempotency
   of a repeated removal at a fixed state.
"""

from __future__ import annotations

import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS
from ..envelope import EOS_MODELS

# Compositions that are firmly single-phase gas across the
# path-independence states below. Two-phase compositions are exercised
# in the remove-liquid block instead.
_SINGLE_PHASE_COMPOSITIONS = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "rich_associated_gas",
    "co2_heavy_injection",
    "n2_heavy",
)

# State pairs are chosen well inside the gas region for every
# single-phase composition above.
_PATH_INDEPENDENCE_STATES = (
    ((20.0, 300.0), (100.0, 340.0)),
    ((50.0, 320.0), (200.0, 350.0)),
    ((10.0, 310.0), (150.0, 380.0)),
)

# State-function properties: must agree across paths.
_STATE_FUNCTION_PROPERTIES = (
    "density",
    "z",
    "kappa",
    "enthalpy_joule_per_kg",
    "molar_mass",
    "vapor_fraction_molar",
)

# Tolerances mirror the regression snapshot's per-property tolerances:
# density / z / kappa converge tightly; enthalpy is integrated and
# carries a small absolute floor; vapor_fraction is exactly 1.0 in the
# single-phase region so an absolute floor suffices.
_PROPERTY_RTOL = {
    "density": 1.0e-8,
    "z": 1.0e-8,
    "kappa": 1.0e-8,
    "molar_mass": 1.0e-12,
    "enthalpy_joule_per_kg": 1.0e-6,
    "vapor_fraction_molar": 0.0,
}
_PROPERTY_ATOL = {
    "density": 0.0,
    "z": 0.0,
    "kappa": 0.0,
    "molar_mass": 0.0,
    "enthalpy_joule_per_kg": 1.0e-2,
    "vapor_fraction_molar": 1.0e-8,
}


def _assert_states_match(reference: NeqsimFluid, candidate: NeqsimFluid, context: str) -> None:
    for prop in _STATE_FUNCTION_PROPERTIES:
        ref = getattr(reference, prop)
        got = getattr(candidate, prop)
        assert math.isfinite(ref) and math.isfinite(got), f"non-finite {prop} {context}: ref={ref!r} got={got!r}"
        rtol = _PROPERTY_RTOL[prop]
        atol = _PROPERTY_ATOL[prop]
        tol = atol + rtol * abs(ref)
        assert abs(got - ref) <= tol, (
            f"{prop} disagrees {context}: reference={ref!r} candidate={got!r} diff={abs(got - ref):.3e} tol={tol:.3e}"
        )


def _create(composition_name: str, pressure_bara: float, temperature_kelvin: float, eos_model) -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        eos_model=eos_model,
    )


_PATH_CASES = [
    pytest.param(
        composition_name,
        start,
        end,
        eos_model,
        id=f"{composition_name}-({start[0]:g}bara,{start[1]:g}K)->({end[0]:g}bara,{end[1]:g}K)-{eos_model.name}",
    )
    for composition_name in _SINGLE_PHASE_COMPOSITIONS
    for start, end in _PATH_INDEPENDENCE_STATES
    for eos_model in EOS_MODELS
]


@pytest.mark.parametrize("composition_name,start,end,eos_model", _PATH_CASES)
def test_tp_flash_state_independent_of_intermediate_path(composition_name, start, end, eos_model):
    """A TP flash to the final state must produce the same fluid no
    matter which intermediate (P, T) path the wrapper takes to get
    there. Tests three paths against the direct flash:

    * pressure first, temperature second (``(P1,T1) -> (P2,T1) -> (P2,T2)``)
    * temperature first, pressure second (``(P1,T1) -> (P1,T2) -> (P2,T2)``)
    * a midpoint detour (``(P1,T1) -> (Pmid,Tmid) -> (P2,T2)``)
    """
    p1, t1 = start
    p2, t2 = end
    pmid, tmid = 0.5 * (p1 + p2), 0.5 * (t1 + t2)

    inlet = _create(composition_name, p1, t1, eos_model)
    direct = inlet.set_new_pressure_and_temperature(p2, t2)

    pressure_first = inlet.set_new_pressure_and_temperature(p2, t1).set_new_pressure_and_temperature(p2, t2)
    temperature_first = inlet.set_new_pressure_and_temperature(p1, t2).set_new_pressure_and_temperature(p2, t2)
    via_midpoint = inlet.set_new_pressure_and_temperature(pmid, tmid).set_new_pressure_and_temperature(p2, t2)

    context = f"on {composition_name} ({eos_model.name}) {start}->{end}"
    _assert_states_match(direct, pressure_first, f"[pressure-first vs direct] {context}")
    _assert_states_match(direct, temperature_first, f"[temperature-first vs direct] {context}")
    _assert_states_match(direct, via_midpoint, f"[via-midpoint vs direct] {context}")


@pytest.mark.parametrize("composition_name,start,end,eos_model", _PATH_CASES)
def test_tp_flash_matches_direct_construction(composition_name, start, end, eos_model):
    """Reaching ``(P2, T2)`` by flashing from a different starting
    point must agree with constructing the fluid directly at
    ``(P2, T2)``. Catches any starting-point bias in the wrapper."""
    p1, t1 = start
    p2, t2 = end

    flashed = _create(composition_name, p1, t1, eos_model).set_new_pressure_and_temperature(p2, t2)
    constructed = _create(composition_name, p2, t2, eos_model)

    _assert_states_match(
        constructed,
        flashed,
        f"[flashed vs direct construction] on {composition_name} ({eos_model.name}) {start}->{end}",
    )


# Two-phase characterisation. c3_rich_wellstream is reliably two-phase
# at moderate pressure / cool temperatures; the dry variant is used for
# the colder probe to stay above the wet-composition floor (no water
# here, so cold T is fine).
_TWO_PHASE_PROBE_CASES = [
    pytest.param(
        composition_name,
        start,
        end,
        eos_model,
        id=f"{composition_name}-({start[0]:g}bara,{start[1]:g}K)->({end[0]:g}bara,{end[1]:g}K)-{eos_model.name}",
    )
    for composition_name, start, end in (
        ("c3_rich_wellstream_dry", (40.0, 270.0), (90.0, 305.0)),
        ("c3_rich_wellstream_dry", (50.0, 280.0), (120.0, 320.0)),
    )
    for eos_model in EOS_MODELS
]


@pytest.mark.parametrize("composition_name,start,end,eos_model", _TWO_PHASE_PROBE_CASES)
def test_remove_liquid_does_not_commute_with_tp_flash(composition_name, start, end, eos_model):
    """``clone_gas_phase`` materially changes the system's mass and
    composition: it cannot commute with a subsequent (or preceding)
    TP flash whenever the two states have different liquid loads.

    Concretely:

    * ``A = remove_liquid_at(P1,T1) -> flash_to(P2,T2)`` carries the
      gas-phase composition at the *initial* state forward, then
      re-flashes that gas-only mixture at the new state.
    * ``B = flash_to(P2,T2) -> remove_liquid_at(P2,T2)`` flashes the
      *original* mixed feed to the new state, then takes whatever gas
      phase exists there.

    A and B describe physically distinct operations and must produce
    different fluids whenever any liquid was present at either state.
    This test pins that they *do* differ (so a future NeqSim version
    that silently made them equal would surface here)."""
    p1, t1 = start
    p2, t2 = end

    inlet = _create(composition_name, p1, t1, eos_model)
    # Sanity precondition: starting state must be two-phase, otherwise
    # the test premise is void (both orders would trivially agree).
    assert inlet.vapor_fraction_molar < 1.0 - 1.0e-6, (
        f"starting state is single-phase on {composition_name} ({eos_model.name}) {start}: "
        f"vapor_fraction_molar={inlet.vapor_fraction_molar!r}"
    )

    a = inlet.clone_gas_phase().set_new_pressure_and_temperature(p2, t2)
    b = inlet.set_new_pressure_and_temperature(p2, t2).clone_gas_phase()

    # Molar mass is the cleanest discriminator: removing liquid first
    # strips heavy ends at (P1,T1), so A's gas is leaner than B's
    # whenever (P1,T1) was meaningfully two-phase.
    delta_molar_mass = abs(a.molar_mass - b.molar_mass)
    assert delta_molar_mass > 1.0e-4, (
        f"order of clone_gas_phase / TP-flash should NOT commute on "
        f"{composition_name} ({eos_model.name}) {start}->{end}, but molar_mass agrees: "
        f"A={a.molar_mass!r} B={b.molar_mass!r}"
    )

    # Both branches must end up as legitimate single-phase gas.
    for label, fluid in (("A", a), ("B", b)):
        assert math.isfinite(fluid.density) and fluid.density > 0.0, (
            f"branch {label} produced a degenerate fluid on {composition_name} ({eos_model.name}) {start}->{end}: "
            f"density={fluid.density!r}"
        )
        assert fluid.vapor_fraction_molar > 1.0 - 1.0e-6, (
            f"branch {label} did not converge to gas-only on {composition_name} ({eos_model.name}) {start}->{end}: "
            f"vapor_fraction_molar={fluid.vapor_fraction_molar!r}"
        )


@pytest.mark.parametrize("composition_name,start,end,eos_model", _TWO_PHASE_PROBE_CASES)
def test_remove_liquid_is_idempotent_at_the_same_state(composition_name, start, end, eos_model):
    """Calling ``clone_gas_phase`` twice in a row at the same (P, T)
    must match a single call: once liquid has been removed, the system
    is gas-only and a second extraction is a no-op. Catches any
    accidental state mutation during repeated phase extraction."""
    del end  # only the starting state is needed here.
    p1, t1 = start

    inlet = _create(composition_name, p1, t1, eos_model)
    once = inlet.clone_gas_phase()
    twice = once.clone_gas_phase()

    _assert_states_match(
        once,
        twice,
        f"[clone_gas_phase idempotency] on {composition_name} ({eos_model.name}) at {start}",
    )
