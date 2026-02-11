from dataclasses import dataclass

import pytest

from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.process_solver import ProcessSolver
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@pytest.fixture
def stage1_chart_data(chart_data_factory) -> ChartData:
    # Higher capacity
    return chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)


@pytest.fixture
def stage2_chart_data(chart_data_factory) -> ChartData:
    # Lower capacity
    return chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)


@dataclass
class ProbeState:
    inlet: FluidStream | None = None
    outlet: FluidStream | None = None
    shaft_speed: float | None = None


class ProbeProcessUnit(ProcessUnit):
    """
    Test helper that wraps another ProcessUnit and records the last inlet/outlet stream
    (and current shaft speed) for assertions.
    """

    def __init__(self, inner: ProcessUnit, shaft: Shaft):
        self._inner = inner
        self._shaft = shaft
        self.state = ProbeState()

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        self.state.inlet = inlet_stream
        self.state.shaft_speed = self._shaft.get_speed()
        outlet = self._inner.propagate_stream(inlet_stream)
        self.state.outlet = outlet
        return outlet


class RateLimiterCompressor(ProcessUnit):
    def __init__(self, minimum_rate_m3_per_hour: float, maximum_rate_m3_per_hour: float):
        self._minimum_rate = minimum_rate_m3_per_hour
        self._maximum_rate = maximum_rate_m3_per_hour

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if inlet_stream.volumetric_rate_m3_per_hour < self._minimum_rate:
            raise RateTooLowError("")
        if inlet_stream.volumetric_rate_m3_per_hour > self._maximum_rate:
            raise RateTooHighError("")
        # Return unchanged pressure; this unit is only a feasibility gate
        return inlet_stream


def test_two_stage_train_speed_solver(
    chart_data_factory,
    process_system_factory,
    stream_constraint_factory,
    search_strategy_factory,
    root_finding_strategy,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    stage1_chart_data,
    stage2_chart_data,
):
    """
    Test the new process_solver stack using a realistic setup.

    Build a two-stage compressor train by chaining two `StageProcessUnit`s in a `ProcessSystem`.
    Both stages share the same `VariableSpeedShaft` (common-shaft train), and each stage uses
    GenericFromDesignPoint chart data.

    The test verifies that `SpeedSolver` can find a shaft speed (within the chart speed range,
    typically [75, 105] for these generic charts) that makes the outlet pressure after both stages
    match the requested target pressure.
    """

    shaft = VariableSpeedShaft()

    # Inlet boundary conditions for the train: fixed rate and suction pressure.
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=1000.0,
        pressure_bara=50.0,
    )

    # Target discharge pressure AFTER both stages.
    target_pressure = 110.0
    stream_constraint = stream_constraint_factory(pressure=target_pressure)

    stage1 = ProbeProcessUnit(
        inner=compressor_train_stage_process_unit_factory(chart_data=stage1_chart_data, shaft=shaft),
        shaft=shaft,
    )
    stage2 = ProbeProcessUnit(
        inner=compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft),
        shaft=shaft,
    )

    # Build a two-stage train:
    # - StageProcessUnit wraps a CompressorTrainStage and raises OutsideCapacityError if the
    #   operating point is not within chart capacity.
    # - Using the same `shaft` instance for both stages models a common-shaft compressor train.
    process_system = process_system_factory(process_units=[stage1, stage2])

    # SpeedSolver needs a speed search interval. For GenericFromDesignPoint charts the available
    # speeds are the chart curve speeds (typically [75, 105]).
    chart_speeds = [curve.speed for curve in stage1_chart_data.get_adjusted_curves()]
    boundary = Boundary(min=min(chart_speeds), max=max(chart_speeds))

    process_solver = ProcessSolver(
        inlet_stream=inlet_stream,
        process_system=process_system,
        solvers=[
            SpeedSolver(
                search_strategy=search_strategy_factory(),
                root_finding_strategy=root_finding_strategy,
                boundary=boundary,
                target_pressure=target_pressure,
                shaft=shaft,
            ),
        ],
        stream_constraint=stream_constraint,
    )

    # Solve for a shaft speed that makes the outlet pressure meet the constraint.
    assert process_solver.find_solution()

    # Verify that running the process system with the solved speed meets the target pressure.
    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == pytest.approx(target_pressure)

    # Optional: assert the actual speed found. This can be sensitive to numerical changes.
    assert shaft.get_speed() == pytest.approx(84.173, abs=0.1)

    # New, 2-stage-specific asserts:

    # 1) Series composition: stage2 inlet is stage1 outlet (same pressure).
    assert stage1.state.outlet is not None
    assert stage2.state.inlet is not None
    assert stage2.state.inlet.pressure_bara == stage1.state.outlet.pressure_bara

    # 2) Common-shaft wiring: both stages evaluated at the same shaft speed.
    assert stage1.state.shaft_speed == shaft.get_speed()
    assert stage2.state.shaft_speed == shaft.get_speed()


def test_two_stage_train_recirculation_then_speed_solver(
    chart_data_factory,
    process_system_factory,
    search_strategy_factory,
    stream_constraint_factory,
    root_finding_strategy,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    fluid_service,
    stage1_chart_data,
    stage2_chart_data,
):
    """
    Run a two-stage (common-shaft) compressor train with a solver chain:

    - RecirculationSolver increases recirculation until the upstream rate limiter is within bounds.
    - SpeedSolver then adjusts shaft speed to hit an outlet pressure target (chosen within the
      min/max outlet pressure achievable over the chart speed range).
    """

    shaft = VariableSpeedShaft()
    inlet_stream = stream_factory(standard_rate_m3_per_day=10000.0, pressure_bara=30.0)

    # Rate limiter compressor is only used to trigger RateTooLow/RateTooHigh so RecirculationSolver has something to solve.
    rate_limited_unit = RateLimiterCompressor(minimum_rate_m3_per_hour=30.0, maximum_rate_m3_per_hour=500.0)
    recirculation_loop = RecirculationLoop(inner_process=rate_limited_unit, fluid_service=fluid_service)

    # Two compressor stages on a shared shaft (common-shaft train).
    stage1 = compressor_train_stage_process_unit_factory(chart_data=stage1_chart_data, shaft=shaft)
    stage2 = compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft)

    # Build full process system
    process_system = process_system_factory(process_units=[recirculation_loop, stage1, stage2])

    recirc_solver = RecirculationSolver(
        search_strategy=search_strategy_factory(tolerance=1e-2),
        root_finding_strategy=root_finding_strategy,
        recirculation_loop=recirculation_loop,
        recirculation_rate_boundary=Boundary(min=0.0, max=20000.0),
        target_pressure=None,
    )

    # Pre-check: without recirculation, the rate limiter should fail at this inlet condition.
    process_system_only_recirc = process_system_factory(process_units=[recirculation_loop])
    with pytest.raises(RateTooLowError):
        process_system_only_recirc.propagate_stream(inlet_stream=inlet_stream)

    # After recirculation solver: Inlet stream should propagate without RateTooLowError.
    recirc_solver.solve(process_system_only_recirc, inlet_stream=inlet_stream)
    process_system_only_recirc.propagate_stream(inlet_stream=inlet_stream)

    # SpeedSolver will evaluate the full system, so the shaft speed must be defined up front.
    chart_speeds = [c.speed for c in stage1_chart_data.get_adjusted_curves()]
    speed_boundary = Boundary(min=min(chart_speeds), max=max(chart_speeds))

    # Set speed and find target pressure for speed solver (between min and max pressure at min speed)
    shaft.set_speed(speed_boundary.max)
    p_max = process_system.propagate_stream(inlet_stream=inlet_stream).pressure_bara

    shaft.set_speed(speed_boundary.min)
    p_min = process_system.propagate_stream(inlet_stream=inlet_stream).pressure_bara

    # Pick a target pressure that is guaranteed to be reachable within the speed boundary.
    target_pressure = (p_min + p_max) / 2

    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=speed_boundary,
        target_pressure=target_pressure,
        shaft=shaft,
    )

    stream_constraint = stream_constraint_factory(pressure=target_pressure)

    process_solver = ProcessSolver(
        inlet_stream=inlet_stream,
        process_system=process_system,
        solvers=[recirc_solver, speed_solver],
        stream_constraint=stream_constraint,
    )

    assert process_solver.find_solution()

    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == pytest.approx(target_pressure, abs=1e-3)

    # Key assertion: recirculation was actually used
    assert recirculation_loop.get_recirculation_rate() > 0.0
    # And shaft speed should end up within chart boundary
    assert speed_boundary.min <= shaft.get_speed() <= speed_boundary.max
