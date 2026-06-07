"""Tests for MultiShaftSolver edge cases."""

import pytest

from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_solver import MultiShaftSolver


def test_mismatched_targets_raises(single_compressor_pipeline_section_factory, stream_factory):
    pipelines = [
        single_compressor_pipeline_section_factory(
            min_rate=200,
            max_rate=5000,
            head_hi=200_000,
            head_lo=140_000,
            inlet_temperature_kelvin=303.15,
        )
    ]
    solver = MultiShaftSolver(pipeline_sections=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    with pytest.raises(AssertionError, match="must match"):
        solver.find_solution([FloatConstraint(50.0), FloatConstraint(100.0)], inlet)


def test_empty_pipelines(stream_factory):
    solver = MultiShaftSolver(pipeline_sections=[])
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution([], inlet)

    assert solution.success
    assert solution.configuration == []
    assert solution.failure is None


def test_unreachable_target_reports_failure(single_compressor_pipeline_section_factory, stream_factory):
    """A target far beyond the chart capability should return success=False."""
    pipelines = [
        single_compressor_pipeline_section_factory(
            min_rate=200,
            max_rate=5000,
            head_hi=200_000,
            head_lo=140_000,
            inlet_temperature_kelvin=303.15,
        )
    ]
    solver = MultiShaftSolver(pipeline_sections=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    # 9000 bara from 30 bara inlet is far beyond what a single stage can deliver
    solution = solver.find_solution([FloatConstraint(9000.0)], inlet)

    assert not solution.success
    assert solution.failure is not None


def test_second_pipeline_failure_preserves_first_failure(single_compressor_pipeline_section_factory, stream_factory):
    """When multiple pipelines fail, the first failure is preserved."""
    pipelines = [
        single_compressor_pipeline_section_factory(
            min_rate=200,
            max_rate=5000,
            head_hi=200_000,
            head_lo=140_000,
            inlet_temperature_kelvin=303.15,
        ),
        single_compressor_pipeline_section_factory(
            min_rate=200,
            max_rate=5000,
            head_hi=200_000,
            head_lo=140_000,
            inlet_temperature_kelvin=303.15,
        ),
    ]
    solver = MultiShaftSolver(pipeline_sections=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    # Both targets unreachable
    solution = solver.find_solution([FloatConstraint(9000.0), FloatConstraint(90000.0)], inlet)

    assert not solution.success
    assert solution.failure is not None
    # Configurations are still collected (best-effort from each pipeline)
    assert len(solution.configuration) > 0
