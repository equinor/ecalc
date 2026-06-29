"""Process-domain solver path matrix tests.

Tests the new PipelineSectionSolver.find_solution() across all 45 trial cases
(9 regions × 5 pressure-control modes). Cases where the process solver does not
yet match legacy behavior are marked as strict xfails.
"""

from __future__ import annotations

import numpy as np
import pytest

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import CompressorStonewallError, CompressorSurgeError
from libecalc.process.process_solver.configuration import (
    ChokeConfiguration,
    RecirculationConfiguration,
    SpeedConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_units.compressor import Compressor

from ..utils import Xfail, make_xfail_param, outcome_from_process_solution
from .assertions import (
    POWER_TOLERANCE,
    PRESSURE_TOLERANCE,
    assert_control_behavior,
    assert_pressure_expectation,
    assert_speed_boundary,
)
from .cases import TEST_CASES, TrialCase

# ---------------------------------------------------------------------------
# Expected failures — remove entries as the process solver improves
# ---------------------------------------------------------------------------
PROCESS_XFAILS: dict[tuple[str, str], Xfail] = {
    # R8: at zero inlet rate, legacy short-circuits to power=0, pressure=NaN (compressor off).
    # The process solver has no zero-rate guard - it solves normally, finding a speed and
    # recirculation rate that hits target pressure with all flow circulating internally
    # (outlet mass rate = 0). Whether this or legacy's behavior is "correct" is a design
    # decision that depends on what zero-rate means operationally.
    ("R8", "UPSTREAM_CHOKE"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
    ("R8", "DOWNSTREAM_CHOKE"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
    ("R8", "INDIVIDUAL_ASV_RATE"): Xfail(
        "Zero-rate: process solver solves normally; legacy short-circuits to power=0."
    ),
    ("R8", "INDIVIDUAL_ASV_PRESSURE"): Xfail(
        "Zero-rate: process solver solves normally; legacy short-circuits to power=0."
    ),
    ("R8", "COMMON_ASV"): Xfail("Zero-rate: process solver solves normally; legacy short-circuits to power=0."),
}


# ---------------------------------------------------------------------------
# Test parametrization and helpers
# ---------------------------------------------------------------------------


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


PROCESS_TEST_PARAMS = tuple(make_xfail_param(case, PROCESS_XFAILS) for case in TEST_CASES)


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
    except CompressorStonewallError:
        outlet_pressure = np.nan

    outcome = outcome_from_process_solution(solution)
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
    except (CompressorStonewallError, CompressorSurgeError):
        pass

    recirculation_rates = tuple(
        c.value.recirculation_rate for c in solution.configuration if isinstance(c.value, RecirculationConfiguration)
    )
    choke_delta_pressure = next(
        (c.value.delta_pressure for c in solution.configuration if isinstance(c.value, ChokeConfiguration)),
        None,
    )

    # Compute the anti-surge floor at the solution speed, without pressure control.
    system.runner.apply_configurations(
        [c for c in solution.configuration if not isinstance(c.value, RecirculationConfiguration)]
    )
    anti_surge_solution = system.pipeline_section.anti_surge_strategy.apply(inlet_stream=inlet_stream)
    anti_surge_recirculation_rates = tuple(c.value.recirculation_rate for c in anti_surge_solution.configuration)

    assert_control_behavior(
        case,
        recirculation_rates=recirculation_rates,
        anti_surge_recirculation_rates=anti_surge_recirculation_rates,
        choke_delta_pressure=choke_delta_pressure,
    )
