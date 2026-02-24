import pytest

from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.compressor_train_solver import (
    CompressorStageProcessUnit,
    CompressorTrainSolver,
)
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def _pressure_at_speed_with_common_asv_feasibility(
    *,
    stages,
    inlet_stream,
    fluid_service,
    shaft,
    speed: float,
    recirc_boundary: Boundary,
) -> float:
    """
    Evaluate outlet pressure at a fixed speed using the same recirculation procedure as COMMON_ASV:
    try recirculation=0 first, and if RateTooLow occurs, increase to the minimum feasible recirculation rate.

    Used only to pick a reachable target pressure for the test.
    """
    shaft.set_speed(speed)

    loop = RecirculationLoop(
        inner_process=ProcessSystem(process_units=stages),
        fluid_service=fluid_service,
    )

    def recirculation_func(cfg: RecirculationConfiguration):
        loop.set_recirculation_rate(cfg.recirculation_rate)
        return loop.propagate_stream(inlet_stream=inlet_stream)

    try:
        loop.set_recirculation_rate(0.0)
        out = loop.propagate_stream(inlet_stream=inlet_stream)
        return float(out.pressure_bara)
    except RateTooLowError:
        recirculation_solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=1e-2),
            root_finding_strategy=ScipyRootFindingStrategy(),
            recirculation_rate_boundary=recirc_boundary,
            target_pressure=None,
        )
        sol = recirculation_solver.solve(recirculation_func)
        if not sol.success:
            raise RuntimeError(
                "Test setup error: No feasible recirculation rate found within boundary at this speed."
            ) from None

        loop.set_recirculation_rate(sol.configuration.recirculation_rate)
        out = loop.propagate_stream(inlet_stream=inlet_stream)
        return float(out.pressure_bara)


def make_variable_speed_chart_data(chart_data_factory, *, min_rate, max_rate, head_hi, head_lo, eff):
    """
    Two speed curves with identical envelope (min/max rate).
    """
    curves = [
        ChartCurve(
            speed_rpm=75.0,
            rate_actual_m3_hour=[min_rate, max_rate],
            polytropic_head_joule_per_kg=[head_hi, head_lo],
            efficiency_fraction=[eff, eff],
        ),
        ChartCurve(
            speed_rpm=105.0,
            rate_actual_m3_hour=[min_rate, max_rate],
            polytropic_head_joule_per_kg=[head_hi * 1.05, head_lo * 1.05],  # Slightly higher at higher speed
            efficiency_fraction=[eff, eff],
        ),
    ]
    return chart_data_factory.from_curves(curves=curves, control_margin=0.0)


class CompressorStageAdapter(CompressorStageProcessUnit):
    """
    Test adapter: adds get_compressor_chart() so CompressorTrainSolverNew can derive boundaries.
    """

    def __init__(self, stage_process_unit: ProcessUnit, chart: CompressorChart):
        self._stage_process_unit = stage_process_unit
        self._chart = chart

    def get_compressor_chart(self) -> CompressorChart:
        return self._chart

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return self._stage_process_unit.propagate_stream(inlet_stream=inlet_stream)


def _reachable_target_pressure_constraint(
    *,
    stages,
    inlet_stream,
    fluid_service,
    shaft,
    speed_boundary,
    recirculation_boundary,
):
    """
    Helper used to avoid code duplication when picking reasonable target pressures.

    """

    p_at_min_speed = _pressure_at_speed_with_common_asv_feasibility(
        stages=stages,
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed=speed_boundary.min,
        recirc_boundary=recirculation_boundary,
    )
    p_at_max_speed = _pressure_at_speed_with_common_asv_feasibility(
        stages=stages,
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed=speed_boundary.max,
        recirc_boundary=recirculation_boundary,
    )

    target_pressure = (p_at_min_speed + p_at_max_speed) / 2
    return target_pressure, FloatConstraint(target_pressure, abs_tol=1e-2)


def test_compressor_train_common_asv_requires_recirculation(
    chart_data_factory,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    fluid_service,
):
    """
    Integration test for COMMON_ASV (shared recirculation) pressure control on a two-stage compressor train.

    The charts are constructed so that stage 1 violates minimum flow at recirculation=0. The solver must then
    find a feasible speed/recirculation combination that meets a reachable outlet-pressure target.

    Assertions:
      - The solution meets the target outlet pressure.
      - The selected shared recirculation rate is > 0.
      - At the solved speed, running with recirculation=0 raises RateTooLowError.
    """

    inlet_stream = stream_factory(standard_rate_m3_per_day=500000.0, pressure_bara=30.0)

    # Use the inlet actual volumetric rate to define a stage-1 minimum flow that is guaranteed
    # to be above the operating point when recirculation=0.
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # Stage 1 is configured to be below minimum flow at recirculation=0 by setting min_rate > q0.
    # Max rate is set sufficiently high so that a feasible point exists after adding recirculation.
    stage1_min_rate = q0 * 1.5
    stage1_max_rate = q0 * 10.0

    stage1_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=stage1_min_rate,
        max_rate=stage1_max_rate,
        head_hi=80000.0,
        head_lo=40000.0,
        eff=0.75,
    )

    # Stage 2 should not be the limiting stage in this test; it is given a wide envelope.
    stage2_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=stage1_max_rate * 2.0,
        head_hi=60000.0,
        head_lo=30000.0,
        eff=0.72,
    )

    # Arrange: two compressor stages on a common shaft
    shaft = VariableSpeedShaft()
    stage1_process_unit = compressor_train_stage_process_unit_factory(chart_data=stage1_chart_data, shaft=shaft)
    stage2_process_unit = compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft)

    stage1 = CompressorStageAdapter(stage_process_unit=stage1_process_unit, chart=CompressorChart(stage1_chart_data))
    stage2 = CompressorStageAdapter(stage_process_unit=stage2_process_unit, chart=CompressorChart(stage2_chart_data))

    compressor_train = ProcessSystem(process_units=[stage1, stage2])

    stages = [stage for stage in compressor_train._process_units if isinstance(stage, CompressorStageProcessUnit)]

    train_solver = CompressorTrainSolver(
        compressors=stages,
        pressure_control="COMMON_ASV",
        fluid_service=fluid_service,
        shaft=shaft,
    )

    # Determine feasible boundaries used by the outer (speed) and inner (recirculation) solvers.
    speed_boundary = train_solver.get_initial_speed_boundary()
    recirculation_boundary = train_solver.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream)

    # Pick a target pressure that is guaranteed to be reachable within the chosen boundaries by
    # sampling the resulting outlet pressure at min and max speed (with COMMON_ASV feasibility enabled).
    target_pressure, pressure_constraint = _reachable_target_pressure_constraint(
        stages=stages,
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed_boundary=speed_boundary,
        recirculation_boundary=recirculation_boundary,
    )

    # Solve using COMMON_ASV: outer loop tunes speed to meet target pressure, inner loop increases shared
    # recirculation only as needed to keep all stages within capacity.
    solution = train_solver.find_common_asv_solution(
        pressure_constraint=pressure_constraint,
        inlet_stream=inlet_stream,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rate > 0.0

    # Validate the solution by re-running the train at the solved speed and recirculation rate.
    # The outlet pressure should match the chosen target pressure within the configured tolerance.
    recirculation_loop = RecirculationLoop(inner_process=compressor_train, fluid_service=fluid_service)
    shaft.set_speed(solution.configuration.speed)
    recirculation_loop.set_recirculation_rate(solution.configuration.recirculation_rate)

    outlet_stream = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    assert float(outlet_stream.pressure_bara) == pytest.approx(
        target_pressure,
        abs=pressure_constraint.abs_tol,
    )

    # COMMON_ASV should be strictly necessary in this constructed case:
    # at the solved speed, running with recirculation=0 must violate the stage-1 minimum-flow constraint.
    recirculation_loop.set_recirculation_rate(0.0)
    with pytest.raises(RateTooLowError):
        recirculation_loop.propagate_stream(inlet_stream=inlet_stream)


def test_compressor_train_common_asv_recirculation_not_needed(
    chart_data_factory,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    fluid_service,
):
    """
    Integration test for COMMON_ASV (shared recirculation) where recirculation is not required.

    The charts are constructed so that stage 1 is within its minimum-flow limit at recirculation=0.
    The solver should therefore meet a reachable outlet-pressure target without applying shared recirculation.

    Assertions:
      - The solution meets the target outlet pressure.
      - The selected shared recirculation rate is 0.
      - Re-evaluating the solved speed with recirculation=0 does not raise RateTooLowError.
    """
    inlet_stream = stream_factory(standard_rate_m3_per_day=500000.0, pressure_bara=30.0)

    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # Stage 1 minimum flow is set comfortably below the inlet operating point,
    # ensuring the train is feasible without any recirculation.
    stage1_min_rate = q0 * 0.5
    stage1_max_rate = q0 * 10.0

    stage1_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=stage1_min_rate,
        max_rate=stage1_max_rate,
        head_hi=80000.0,
        head_lo=40000.0,
        eff=0.75,
    )

    # Stage 2 should not be limiting; give it a wide envelope as well.
    stage2_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=q0 * 0.1,
        max_rate=stage1_max_rate * 2.0,
        head_hi=60000.0,
        head_lo=30000.0,
        eff=0.72,
    )

    shaft = VariableSpeedShaft()
    stage1_process_unit = compressor_train_stage_process_unit_factory(chart_data=stage1_chart_data, shaft=shaft)
    stage2_process_unit = compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft)

    stage1 = CompressorStageAdapter(stage_process_unit=stage1_process_unit, chart=CompressorChart(stage1_chart_data))
    stage2 = CompressorStageAdapter(stage_process_unit=stage2_process_unit, chart=CompressorChart(stage2_chart_data))

    compressor_train = ProcessSystem(process_units=[stage1, stage2])

    stages = [stage for stage in compressor_train._process_units if isinstance(stage, CompressorStageProcessUnit)]

    train_solver = CompressorTrainSolver(
        compressors=stages,
        pressure_control="COMMON_ASV",
        fluid_service=fluid_service,
        shaft=shaft,
    )

    speed_boundary = train_solver.get_initial_speed_boundary()
    recirculation_boundary = train_solver.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream)

    # Pick a target pressure that is guaranteed to be reachable within the chosen boundaries by
    # sampling the resulting outlet pressure at min and max speed (with COMMON_ASV feasibility enabled).
    target_pressure, pressure_constraint = _reachable_target_pressure_constraint(
        stages=stages,
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed_boundary=speed_boundary,
        recirculation_boundary=recirculation_boundary,
    )

    solution = train_solver.find_common_asv_solution(
        pressure_constraint=pressure_constraint,
        inlet_stream=inlet_stream,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rate == 0.0

    # Validate by re-running the train at the solved speed with recirculation=0 and verifying target pressure.
    recirculation_loop = RecirculationLoop(inner_process=compressor_train, fluid_service=fluid_service)
    shaft.set_speed(solution.configuration.speed)
    recirculation_loop.set_recirculation_rate(0.0)

    outlet_stream = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    assert float(outlet_stream.pressure_bara) == pytest.approx(
        target_pressure,
        abs=pressure_constraint.abs_tol,
    )
