from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver


def test_upstream_choke_solver(
    root_finding_strategy,
    simple_process_unit_factory,
    fluid_service,
    stream_factory,
    choke_factory,
):
    choke = choke_factory()
    process_units = [choke, simple_process_unit_factory(pressure_multiplier=1)]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=70,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_stream.pressure_bara - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        choke.set_pressure_change(configuration.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    assert upstream_choke_solver.solve(choke_func)
    outlet_stream = propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    assert outlet_stream.pressure_bara == 70


def test_upstream_choke_solver_handles_rate_too_high_at_max_choke(
    root_finding_strategy,
    stream_factory,
):
    """
    When the upstream choke drops suction pressure so low that the downstream process unit
    raises RateTooHighError (actual volumetric rate diverges), the solver must still converge
    to the correct choke setting rather than propagating the exception.
    """
    inlet_pressure = 100.0
    # The downstream unit fails below this suction pressure (simulates a chart-limited compressor).
    feasible_suction_pressure = 20.0
    pressure_added = 50.0

    # Baseline outlet = 100 + 50 = 150. Target below that requires choking.
    # Required delta_p = inlet - (target - pressure_added) = 100 - (80 - 50) = 70.
    target_pressure = 80.0

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        if suction_pressure < feasible_suction_pressure:
            # TODO: Should get ID from owning choke?
            raise RateTooHighError(process_unit_id=ProcessUnitId(ecalc_id_generator()))
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    solution = upstream_choke_solver.solve(choke_func)

    assert solution.success
    assert abs(solution.configuration.delta_pressure - 70.0) < 1e-3


def test_upstream_choke_solver_reports_failure_when_rate_capacity_prevents_reaching_target(
    root_finding_strategy,
    stream_factory,
):
    """When RateTooHighError creates a discontinuity that prevents the outlet from reaching
    the target, the solver must report failure rather than false success at the discontinuity boundary.

    Scenario: outlet = inlet - dp + 50. RateTooHighError at dp > 40 (suction < 60).
    Target = 80 requires dp = 70, which is in the infeasible region.
    Root-finding converges at dp ≈ 40 (discontinuity boundary) where actual outlet = 110, not 80.
    """
    inlet_pressure = 100.0
    feasible_suction_minimum = 60.0  # RateTooHighError below this
    pressure_added = 50.0
    target_pressure = 80.0  # Requires dp=70, infeasible (max feasible dp=40)

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        if suction_pressure < feasible_suction_minimum:
            raise RateTooHighError(process_unit_id=ProcessUnitId(ecalc_id_generator()))
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    solution = upstream_choke_solver.solve(choke_func)

    assert not solution.success
    assert solution.failure_event is not None
    assert solution.failure_event.target_value == target_pressure
    assert solution.failure_event.achievable_value > target_pressure


def test_upstream_choke_solver_reports_failure_when_max_choke_still_above_target(
    root_finding_strategy,
    stream_factory,
):
    inlet_pressure = 100.0
    pressure_added = 200.0
    target_pressure = 80.0  # max choke gives ~0 + 200 = 200, still above 80

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    solution = upstream_choke_solver.solve(choke_func)

    assert not solution.success
    assert solution.failure_event is not None
    assert solution.failure_event.target_value == target_pressure
    assert solution.failure_event.achievable_value > target_pressure
