"""Compare MultiShaftEqualRatioSolver outlet against CompressorTrainSimplified (legacy).

Both models split the overall pressure target into equal per-stage ratios.
"""

import pytest

from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train import CompressorTrainSimplified
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_equal_ratio_solver import MultiShaftEqualRatioSolver
from tests.libecalc.process.process_solver.test_multi_shaft_equal_ratio_solver import (
    make_process_pipeline,
    make_variable_speed_chart,
)

_RATE_SM3_DAY = 1_500_000.0
_P_IN_BARA = 30.0
_P_OUT_BARA = 270.0
_T_IN_KELVIN = 303.15
_N_STAGES = 3
_HEAD_HI = 200_000.0
_HEAD_LO = 140_000.0
_MIN_RATE = 200.0
_MAX_RATE = 5_000.0


def test_multi_shaft_outlet_pressure_matches_simplified_train(
    stream_factory,
    fluid_service,
    root_finding_strategy,
    compressor_stage_factory,
):
    """Outlet pressure should match within 1% relative tolerance."""
    # Legacy: CompressorTrainSimplified
    chart_data = make_variable_speed_chart(_MIN_RATE, _MAX_RATE, _HEAD_HI, _HEAD_LO)
    legacy_stages = [
        compressor_stage_factory(compressor_chart_data=chart_data, inlet_temperature_kelvin=_T_IN_KELVIN)
        for _ in range(_N_STAGES)
    ]
    legacy_train = CompressorTrainSimplified(stages=legacy_stages, fluid_service=fluid_service)
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=_RATE_SM3_DAY,
        pressure_bara=_P_IN_BARA,
        temperature_kelvin=_T_IN_KELVIN,
    )
    legacy_train._fluid_model = [inlet_stream.fluid_model]
    legacy_result = legacy_train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            suction_pressure=_P_IN_BARA,
            discharge_pressure=_P_OUT_BARA,
            rates=[_RATE_SM3_DAY],
        )
    )
    legacy_outlet = legacy_result.outlet_stream

    # New: MultiShaftEqualRatioSolver
    solver_pipelines = [
        make_process_pipeline(
            min_rate=_MIN_RATE,
            max_rate=_MAX_RATE,
            head_hi=_HEAD_HI,
            head_lo=_HEAD_LO,
            inlet_temperature_kelvin=_T_IN_KELVIN,
            fluid_service=fluid_service,
            root_finding_strategy=root_finding_strategy,
        )
        for _ in range(_N_STAGES)
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=solver_pipelines)
    solution = solver.find_solution(FloatConstraint(_P_OUT_BARA, abs_tol=1.0), inlet_stream)

    assert solution.success, f"Solver failed: {solution.failure_event}"

    current = inlet_stream
    for pipeline in solver_pipelines:
        current = pipeline.runner.run(current)
    new_outlet = current

    assert new_outlet.pressure_bara == pytest.approx(legacy_outlet.pressure_bara, rel=0.01)
    assert new_outlet.temperature_kelvin == pytest.approx(legacy_outlet.temperature_kelvin, rel=0.01)
    assert new_outlet.density == pytest.approx(legacy_outlet.density, rel=0.01)
