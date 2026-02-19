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
    Evaluate outlet pressure at a fixed speed using the SAME recirculation policy as COMMON_ASV:
    start with recirc=0, and if RateTooLow occurs, increase to the minimum feasible recirc.
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
        # Find the minimum recirc that makes the train feasible at this speed
        # (pressure is not constrained here).
        recirculation_solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=1e-2),
            root_finding_strategy=ScipyRootFindingStrategy(),
            recirculation_rate_boundary=recirc_boundary,
            target_pressure=None,
        )
        sol = recirculation_solver.solve(recirculation_func)
        loop.set_recirculation_rate(sol.configuration.recirculation_rate)
        out = loop.propagate_stream(inlet_stream=inlet_stream)
        return float(out.pressure_bara)


class CompressorStageAdapter(CompressorStageProcessUnit):
    """
    Test adapter: adds get_compressor_chart() so CompressorTrainSolverNew can derive boundaries.
    """

    def __init__(self, inner_stage_process_unit: ProcessUnit, chart: CompressorChart):
        self._inner = inner_stage_process_unit
        self._chart = chart

    def get_compressor_chart(self) -> CompressorChart:
        return self._chart

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return self._inner.propagate_stream(inlet_stream=inlet_stream)


def test_compressor_train_solver_with_common_asv(
    chart_data_factory,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    fluid_service,
):
    """
    COMMON_ASV integration test for a two-stage compressor train.

    Verifies that SpeedSolver (outer) and RecirculationSolver (inner) work together on a real train model:
    speed is tuned to meet a reachable outlet-pressure target, while recirculation is applied only as needed
    to keep the train within capacity (avoid RateTooLow).
    """

    inlet_stream = stream_factory(standard_rate_m3_per_day=500000.0, pressure_bara=30.0)

    # Arrange: two compressor stages on a common shaft
    shaft = VariableSpeedShaft()

    stage1_chart_data = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
    stage2_chart_data = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

    stage1_inner = compressor_train_stage_process_unit_factory(chart_data=stage1_chart_data, shaft=shaft)
    stage2_inner = compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft)

    stage1 = CompressorStageAdapter(inner_stage_process_unit=stage1_inner, chart=CompressorChart(stage1_chart_data))
    stage2 = CompressorStageAdapter(inner_stage_process_unit=stage2_inner, chart=CompressorChart(stage2_chart_data))

    compressor_train = ProcessSystem(process_units=[stage1, stage2])
    compressors = [stage for stage in compressor_train._process_units if isinstance(stage, CompressorStageProcessUnit)]

    train_solver = CompressorTrainSolver(
        compressors=compressors,
        pressure_control="COMMON_ASV",
        fluid_service=fluid_service,
        shaft=shaft,
    )

    # Find speed- and recirculation boundaries.
    speed_boundary = train_solver.get_initial_speed_boundary()
    recirculation_boundary = train_solver.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream)

    # Choose a reachable target pressure, given the speed and recirculation boundaries.
    p_at_min_speed = _pressure_at_speed_with_common_asv_feasibility(
        stages=[stage1, stage2],
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed=speed_boundary.min,
        recirc_boundary=recirculation_boundary,
    )

    p_at_max_speed = _pressure_at_speed_with_common_asv_feasibility(
        stages=[stage1, stage2],
        inlet_stream=inlet_stream,
        fluid_service=fluid_service,
        shaft=shaft,
        speed=speed_boundary.max,
        recirc_boundary=recirculation_boundary,
    )
    target_pressure = (p_at_min_speed + p_at_max_speed) / 2
    pressure_constraint = FloatConstraint(target_pressure, abs_tol=1e-2)

    # Solve using COMMON_ASV
    # (speed outer, recirc inner)
    solution = train_solver.find_common_asv_solution(
        pressure_constraint=pressure_constraint,
        inlet_stream=inlet_stream,
    )

    # Assert: solution found and within boundaries
    assert solution.success is True
    assert speed_boundary.min <= solution.configuration.speed <= speed_boundary.max
    assert recirculation_boundary.min <= solution.configuration.recirculation_rate <= recirculation_boundary.max

    # Propagate inlet stream through the train with the solved speed and recirculation,
    # and assert outlet pressure meets target.
    recirculation_loop = RecirculationLoop(
        inner_process=compressor_train,
        fluid_service=fluid_service,
    )
    shaft.set_speed(solution.configuration.speed)
    recirculation_loop.set_recirculation_rate(solution.configuration.recirculation_rate)

    outlet_stream = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    assert float(outlet_stream.pressure_bara) == pytest.approx(
        target_pressure,
        abs=pressure_constraint.abs_tol,
    )
