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
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
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
    # COMMON_ASV multi-stage: the single common recirculation loop is sized from the
    # LP stage and overloads the narrower HP stage, which raises RateTooHighError
    # (uncaught) instead of returning a structured ABOVE_MAX_FLOW failure.
    ("M1", "COMMON_ASV"): Xfail(
        "Common-ASV single loop overloads HP stage; raises instead of ABOVE_MAX_FLOW.",
        raises=RateTooHighError,
    ),
    ("M2", "COMMON_ASV"): Xfail(
        "Common-ASV single loop overloads HP stage; raises instead of ABOVE_MAX_FLOW.",
        raises=RateTooHighError,
    ),
    ("M4", "COMMON_ASV"): Xfail("Common-ASV power diverges from legacy."),
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

    if case.region.rate_sm3_day == 0.0:
        outlet_pressure = np.nan
    else:
        try:
            outlet_stream = system.runner.run(inlet_stream=inlet_stream)
            outlet_pressure = outlet_stream.pressure_bara
        except RateTooHighError:
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

    if case.region.rate_sm3_day == 0.0:
        return  # Zero-rate: power=0, no chart operating point to validate

    # ── Assert: power, per stage and summed ──────────────────────────────
    try:
        compressor_inlets = [
            system.runner.run(inlet_stream=inlet_stream, to_id=comp.get_id()) for comp in system.compressors
        ]
        per_stage_power = _per_stage_compressor_power_mw(list(system.compressors), compressor_inlets)
        assert sum(per_stage_power) == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
        assert_stage_power(case, tuple(per_stage_power))
    except (RateTooHighError, RateTooLowError):
        pass

    # ── Assert: per-stage anti-surge recirculation ───────────────────────
    recirculation_rates = tuple(
        configuration.value.recirculation_rate
        for configuration in solution.configuration
        if isinstance(configuration.value, RecirculationConfiguration)
    )
    assert_stage_recirculation(case, recirculation_rates)
