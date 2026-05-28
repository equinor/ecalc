"""Process-domain solver path matrix tests.

Tests the new OutletPressureSolver.find_solution() across all 45 trial cases
(9 regions × 5 pressure-control modes). Cases where the process solver does not
yet match legacy behavior are marked as strict xfails.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
    RecirculationConfiguration,
    SpeedConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.solver import (
    RateTooLowFailure as SolverRateTooLowFailure,
)
from libecalc.process.process_units.compressor import Compressor

from .assertions import (
    POWER_TOLERANCE,
    PRESSURE_TOLERANCE,
    assert_control_behavior,
    assert_pressure_expectation,
    assert_speed_boundary,
)
from .cases import TEST_CASES, ExpectedOutcome, TrialCase

# ---------------------------------------------------------------------------
# Expected failures — remove entries as the process solver improves
# ---------------------------------------------------------------------------
PROCESS_XFAILS: dict[tuple[str, str], str] = {
    # R8 — process solver does not implement legacy zero-rate short-circuit
    ("R8", "UPSTREAM_CHOKE"): "No zero-rate short-circuit in process solver.",
    ("R8", "DOWNSTREAM_CHOKE"): "No zero-rate short-circuit in process solver.",
    ("R8", "INDIVIDUAL_ASV_RATE"): "No zero-rate short-circuit in process solver.",
    ("R8", "INDIVIDUAL_ASV_PRESSURE"): "No zero-rate short-circuit in process solver.",
    ("R8", "COMMON_ASV"): "No zero-rate short-circuit in process solver.",
    # R9 — individual case mismatches
    ("R9", "UPSTREAM_CHOKE"): "Upstream-choke strategy reports success for stonewall-limited over-compression.",
    ("R9", "COMMON_ASV"): "Common-ASV reports pressure-limit where legacy reports stonewall for R9.",
}


# ---------------------------------------------------------------------------
# Test parametrization and helpers
# ---------------------------------------------------------------------------


def _outcome_from_process_solution(
    solution: Solution[Sequence[Configuration]],
) -> ExpectedOutcome:
    if solution.success:
        return ExpectedOutcome.SUCCESS
    if solution.failure is None:
        return ExpectedOutcome.NOT_CALCULATED
    match solution.failure:
        case RateTooHighFailure():
            return ExpectedOutcome.ABOVE_MAX_FLOW
        case SolverRateTooLowFailure():
            return ExpectedOutcome.BELOW_MIN_FLOW
        case TargetPressureUnreachableFailure(direction=TargetDirection.MAX_BELOW_TARGET):
            return ExpectedOutcome.PRESSURE_TOO_HIGH
        case TargetPressureUnreachableFailure(direction=TargetDirection.MIN_ABOVE_TARGET):
            return ExpectedOutcome.PRESSURE_TOO_LOW
        case _:
            return ExpectedOutcome.NOT_CALCULATED


def _calculate_compressor_power_mw(
    compressor: Compressor,
    compressor_inlet_stream: FluidStream,
) -> float:
    """Calculate compressor power [MW] from inlet/outlet enthalpy difference.

    Power = Δh × ṁ, where Δh = (h_outlet - h_inlet) [J/kg]
    and ṁ is the mass rate through the compressor (including recirculation).
    """
    compressor_outlet_stream = compressor.propagate_stream(compressor_inlet_stream)
    delta_h = compressor_outlet_stream.enthalpy_joule_per_kg - compressor_inlet_stream.enthalpy_joule_per_kg
    mass_rate = compressor_inlet_stream.mass_rate_kg_per_h
    return delta_h * mass_rate / 3600.0 / 1e6


PROCESS_TEST_PARAMS = tuple(
    pytest.param(
        case,
        id=case.id,
        marks=pytest.mark.xfail(reason=PROCESS_XFAILS[(case.region.id, case.mode)], strict=True),
    )
    if (case.region.id, case.mode) in PROCESS_XFAILS
    else pytest.param(case, id=case.id)
    for case in TEST_CASES
)


@pytest.mark.parametrize("case", PROCESS_TEST_PARAMS)
def test_process_solver_path(
    case: TrialCase,
    variable_speed_compressor_chart_data,
    process_solver_case_factory,
):
    system, inlet_stream = process_solver_case_factory(chart_data=variable_speed_compressor_chart_data, case=case)

    solution = system.solver.find_solution(
        pressure_constraint=FloatConstraint(case.region.discharge_pressure_bara, abs_tol=PRESSURE_TOLERANCE),
        inlet_stream=inlet_stream,
    )
    system.runner.apply_configurations(solution.configuration)
    try:
        outlet_stream = system.runner.run(inlet_stream=inlet_stream)
        outlet_pressure = outlet_stream.pressure_bara
    except RateTooHighError:
        outlet_pressure = np.nan

    outcome = _outcome_from_process_solution(solution)
    speed = next(
        (c.value.speed for c in solution.configuration if isinstance(c.value, SpeedConfiguration)),
        system.shaft.get_speed(),
    )

    assert solution.success is case.expectation.success
    assert outcome is case.expectation.outcome
    assert_pressure_expectation(outlet_pressure, case)
    assert_speed_boundary(speed, variable_speed_compressor_chart_data, case)

    # Power assertion: compute from compressor inlet/outlet enthalpy difference.
    # Skipped when the compressor rejects the operating point (e.g. R5 above-max-flow),
    # since the process solver doesn't extrapolate beyond the chart like legacy does.
    compressor = system.compressors[0]
    try:
        compressor_inlet = system.runner.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
        power_mw = _calculate_compressor_power_mw(compressor, compressor_inlet)
        assert power_mw == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
    except (RateTooHighError, RateTooLowError):
        pass

    recirculation_rates = tuple(
        c.value.recirculation_rate for c in solution.configuration if isinstance(c.value, RecirculationConfiguration)
    )
    choke_delta_pressure = next(
        (c.value.delta_pressure for c in solution.configuration if isinstance(c.value, ChokeConfiguration)),
        None,
    )
    anti_surge_solution = system.solver.get_anti_surge_solution()
    anti_surge_recirculation_rates = (
        tuple(c.value.recirculation_rate for c in anti_surge_solution.configuration)
        if anti_surge_solution is not None
        else ()
    )
    assert_control_behavior(
        case,
        recirculation_rates=recirculation_rates,
        anti_surge_recirculation_rates=anti_surge_recirculation_rates,
        choke_delta_pressure=choke_delta_pressure,
    )
