"""Tests for MultiShaftEqualRatioSolver."""

import pytest

from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_equal_ratio_solver import MultiShaftEqualRatioSolver


@pytest.fixture
def pipeline_kwargs():
    return {
        "head_hi": 200_000,
        "head_lo": 140_000,
        "inlet_temperature_kelvin": 303.15,
    }


def test_three_shaft_train_hits_target_pressure(
    stream_factory, pipeline_kwargs, single_compressor_process_pipeline_factory
):
    pipelines = [
        single_compressor_process_pipeline_factory(min_rate=200, max_rate=5000, **pipeline_kwargs),
        single_compressor_process_pipeline_factory(min_rate=150, max_rate=3500, **pipeline_kwargs),
        single_compressor_process_pipeline_factory(min_rate=100, max_rate=2500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    assert solution.success, f"Expected success; failure: {solution.failure}"


def test_each_shaft_runs_at_different_speed(
    stream_factory, pipeline_kwargs, single_compressor_process_pipeline_factory
):
    """Real-gas effects cause each pipeline to need a different shaft speed."""
    pipelines = [
        single_compressor_process_pipeline_factory(min_rate=200, max_rate=5000, **pipeline_kwargs),
        single_compressor_process_pipeline_factory(min_rate=150, max_rate=3500, **pipeline_kwargs),
        single_compressor_process_pipeline_factory(min_rate=100, max_rate=2500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    speeds = [c.value.speed for c in solution.configuration if isinstance(c.value, SpeedConfiguration)]
    assert len(speeds) == 3
    assert len(set(speeds)) == 3, f"expected three distinct speeds, got {speeds}"


def test_intercooler_changes_stage_speed(
    stream_factory, fluid_service, root_finding_strategy, single_compressor_process_pipeline_factory
):
    """Warmer inlet temperature changes the required shaft speed."""
    common = {
        "min_rate": 200,
        "max_rate": 5000,
        "head_hi": 200_000,
        "head_lo": 140_000,
    }

    cool = [single_compressor_process_pipeline_factory(**common, inlet_temperature_kelvin=303.15) for _ in range(3)]
    warm = [single_compressor_process_pipeline_factory(**common, inlet_temperature_kelvin=360.0) for _ in range(3)]

    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)
    constraint = FloatConstraint(270.0, abs_tol=5.0)

    sol_cool = MultiShaftEqualRatioSolver(process_pipelines=cool).find_solution(constraint, inlet)
    sol_warm = MultiShaftEqualRatioSolver(process_pipelines=warm).find_solution(constraint, inlet)

    assert sol_cool.success and sol_warm.success

    speeds_cool = [c.value.speed for c in sol_cool.configuration if isinstance(c.value, SpeedConfiguration)]
    speeds_warm = [c.value.speed for c in sol_warm.configuration if isinstance(c.value, SpeedConfiguration)]

    assert speeds_cool[0] != speeds_warm[0]
    assert speeds_cool[1] != speeds_warm[1]


def test_empty_pipelines(stream_factory):
    solver = MultiShaftEqualRatioSolver(process_pipelines=[])
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    assert solution.success
    assert solution.configuration == []
    assert solution.failure is None


def test_single_pipeline_hits_exact_target(stream_factory, pipeline_kwargs, single_compressor_process_pipeline_factory):
    """With one pipeline the target is the exact constraint (no intermediate splitting)."""
    pipeline = single_compressor_process_pipeline_factory(min_rate=200, max_rate=5000, **pipeline_kwargs)
    solver = MultiShaftEqualRatioSolver(process_pipelines=[pipeline])
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(60.0, abs_tol=0.5), inlet)

    assert solution.success
    pipeline.runner.apply_configurations(solution.configuration)
    outlet = pipeline.runner.run(inlet)
    assert outlet.pressure_bara == pytest.approx(60.0, abs=0.5)


def test_two_pipeline_intermediate_target_is_geometric_mean(
    stream_factory, pipeline_kwargs, single_compressor_process_pipeline_factory
):
    """With two pipelines the intermediate target should be sqrt(P_in * P_out)."""
    pipelines = [
        single_compressor_process_pipeline_factory(min_rate=200, max_rate=5000, **pipeline_kwargs),
        single_compressor_process_pipeline_factory(min_rate=150, max_rate=3500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(120.0, abs_tol=1.0), inlet)

    assert solution.success
    # First pipeline should target sqrt(30 * 120) ≈ 60 bara
    intermediate = pipelines[0].runner.run(inlet)
    assert intermediate.pressure_bara == pytest.approx(60.0, abs=1.0)
