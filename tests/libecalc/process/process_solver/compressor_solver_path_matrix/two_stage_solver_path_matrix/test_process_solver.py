"""Process-domain solver path matrix tests — two-stage compressor train.

Tests the PipelineSectionSolver.find_solution() across all 30 trial cases
(6 regions × 5 pressure-control modes) for a two-stage LP + HP configuration.
Cases where the process solver does not yet match legacy behavior are marked
as strict xfails.
"""

from __future__ import annotations

import numpy as np
import pytest

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import CompressorStonewallError, CompressorSurgeError
from libecalc.process.process_solver.configuration import (
    RecirculationConfiguration,
    SpeedConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_units.compressor import Compressor

from ..utils import Xfail, make_xfail_param, outcome_from_process_solution
from .assertions import (
    POWER_TOLERANCE,
    PRESSURE_TOLERANCE,
    assert_pressure_expectation,
    assert_speed_boundary,
    assert_stage_power,
    assert_stage_recirculation,
)
from .cases import TEST_CASES, TwoStageTrialCase

# ---------------------------------------------------------------------------
# Expected failures — remove entries as the process solver improves
# ---------------------------------------------------------------------------
PROCESS_XFAILS: dict[tuple[str, str], Xfail] = {
    # M1-UPSTREAM_CHOKE: process solver reports NOT_CALCULATED instead of ABOVE_MAX_FLOW
    # when upstream choke pushes HP stage above max at low target discharge.
    ("M1", "UPSTREAM_CHOKE"): Xfail("Upstream choke failure not classified as ABOVE_MAX_FLOW."),
    # M1/M2-COMMON_ASV: process solver returns PRESSURE_TOO_LOW (can't reduce pressure
    # within feasible common-ASV recirculation range) while legacy returns ABOVE_MAX_FLOW.
    # Both are valid descriptions of the same physical situation.
    ("M1", "COMMON_ASV"): Xfail(
        "Common-ASV failure classified as PRESSURE_TOO_LOW instead of legacy's ABOVE_MAX_FLOW."
    ),
    ("M2", "COMMON_ASV"): Xfail(
        "Common-ASV failure classified as PRESSURE_TOO_LOW instead of legacy's ABOVE_MAX_FLOW."
    ),
    # M4-COMMON_ASV: process solver succeeds but at higher power (11.87 vs 11.19 MW).
    # Legacy applies per-stage anti-surge (only HP recirculates 648K, LP stays at 0)
    # even in COMMON_ASV mode. Process solver uses the actual common loop topology
    # where anti-surge recirculation flows through both stages.
    ("M4", "COMMON_ASV"): Xfail(
        "Common-ASV anti-surge topology differs: process uses common loop, legacy uses per-stage."
    ),
    # M7-COMMON_ASV: legacy checks chart area flag against the PRE-ASV rate (2336 m3/h)
    # but computes head/efficiency at the ASV-corrected rate (2742 m3/h). The process
    # solver checks the full flow (2742) against the speed-based max (2527) and correctly
    # rejects it. Legacy reports INTERNAL_POINT because 2336 < 2527, even though the
    # compressor physically processes 2742 m3/h.
    ("M7", "COMMON_ASV"): Xfail("Legacy checks chart area at pre-ASV rate; process solver checks at full flow."),
    # M6: at zero inlet rate, legacy short-circuits to power=0, pressure=NaN (compressor off).
    # The process solver has no zero-rate guard - it solves normally, finding a speed and
    # recirculation rate that hits target pressure with all flow circulating internally.
    # Whether this or legacy's behavior is "correct" is a design decision.
    ("M6", "UPSTREAM_CHOKE"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
    ("M6", "DOWNSTREAM_CHOKE"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
    ("M6", "COMMON_ASV"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
    ("M6", "INDIVIDUAL_ASV_RATE"): Xfail(
        "Zero-rate: process solver solves normally; legacy short-circuits to power=0."
    ),
    ("M6", "INDIVIDUAL_ASV_PRESSURE"): Xfail(
        "Zero-rate: process solver solves normally; legacy short-circuits to power=0."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _per_stage_compressor_power_mw(
    compressors: list[Compressor],
    compressor_inlet_streams: list[FluidStream],
) -> list[float]:
    """Power [MW] for each compressor stage: Δh × ṁ."""
    powers = []
    for compressor, inlet in zip(compressors, compressor_inlet_streams, strict=True):
        outlet = compressor.propagate_stream(inlet)
        delta_h = outlet.enthalpy_joule_per_kg - inlet.enthalpy_joule_per_kg
        powers.append(delta_h * inlet.mass_rate_kg_per_h / 3600.0 / 1e6)
    return powers


# ---------------------------------------------------------------------------
# Test parametrization
# ---------------------------------------------------------------------------

PROCESS_TEST_PARAMS = tuple(make_xfail_param(case, PROCESS_XFAILS) for case in TEST_CASES)


@pytest.mark.parametrize("case", PROCESS_TEST_PARAMS)
def test_two_stage_process_solver_path(
    case: TwoStageTrialCase,
    variable_speed_compressor_chart_data,
    hp_compressor_chart_data,
    two_stage_process_case_factory,
):
    # ── Arrange ──────────────────────────────────────────────────────────
    system, inlet_stream = two_stage_process_case_factory(
        lp_chart_data=variable_speed_compressor_chart_data,
        hp_chart_data=hp_compressor_chart_data,
        case=case,
    )

    # ── Act ──────────────────────────────────────────────────────────────
    solution = system.solver.find_solution(
        pressure_constraint=FloatConstraint(case.region.discharge_pressure_bara, abs_tol=PRESSURE_TOLERANCE),
        inlet_stream=inlet_stream,
    )
    system.runner.apply_configurations(solution.configuration)
    try:
        outlet_stream = system.runner.run(inlet_stream=inlet_stream)
        outlet_pressure = outlet_stream.pressure_bara
    except CompressorStonewallError:
        outlet_pressure = np.nan

    outcome = outcome_from_process_solution(solution)
    speed = next(
        (c.value.speed for c in solution.configuration if isinstance(c.value, SpeedConfiguration)),
        system.shaft.get_speed(),
    )

    # ── Assert: outcome ──────────────────────────────────────────────────
    assert solution.success is case.expectation.success
    assert outcome is case.expectation.outcome

    # ── Assert: pressure and speed ───────────────────────────────────────
    assert_pressure_expectation(outlet_pressure, case)
    if case.expectation.success:
        assert_speed_boundary(speed, variable_speed_compressor_chart_data, case)

    # ── Assert: power, per stage and summed ──────────────────────────────
    try:
        compressor_inlets = [
            system.runner.run(inlet_stream=inlet_stream, to_id=comp.get_id()) for comp in system.compressors
        ]
        per_stage_power = _per_stage_compressor_power_mw(list(system.compressors), compressor_inlets)
        assert sum(per_stage_power) == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
        assert_stage_power(case, tuple(per_stage_power))
    except (CompressorStonewallError, CompressorSurgeError):
        pass

    # ── Assert: per-stage anti-surge recirculation ───────────────────────
    recirculation_rates = tuple(
        configuration.value.recirculation_rate
        for configuration in solution.configuration
        if isinstance(configuration.value, RecirculationConfiguration)
    )
    assert_stage_recirculation(case, recirculation_rates)
