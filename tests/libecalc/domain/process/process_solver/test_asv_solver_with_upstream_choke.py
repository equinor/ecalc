from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint


def test_asv_solver_applies_upstream_choke_when_speed_solution_is_at_min_speed(
    stream_factory,
    process_system_factory,
    fluid_service,
    choke_factory,
    speed_compressor_factory,
):
    """
    If the outlet pressure is higher than the target outlet pressure at minimum speed, SpeedSolver returns
    success=False and selects the minimum speed. ASVSolver should still attempt pressure control, and with an
    upstream choke it should be able to meet the target.
    """
    shaft = VariableSpeedShaft()
    upstream_choke = choke_factory()

    # One "compressor" stage that increases pressure with speed, with an upstream choke.
    compressor = speed_compressor_factory(shaft=shaft)

    solver = ASVSolver(
        shaft=shaft,
        process_items=[compressor],
        fluid_service=fluid_service,
        individual_asv_control=False,
        upstream_choke=upstream_choke,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=25.0)

    # At min speed=200 => baseline outlet pressure = 25 + 200 = 225.
    # Choose a target lower than 225 (outlet > target) so SpeedSolver returns min speed with success=False.
    target_pressure = FloatConstraint(210, abs_tol=1e-12)

    speed_solution, recirculation_solutions = solver.find_asv_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )

    # SpeedSolver could not meet the target pressure within the speed boundary,
    # so it returned the minimum speed as the best feasible speed.
    assert speed_solution.success is False
    assert speed_solution.configuration.speed == compressor.get_speed_boundary().min

    # But overall solver should succeed via upstream choke pressure control.
    assert recirculation_solutions[0].success is True

    # Verify that upstream choking actually brings outlet down to target.
    process_system = process_system_factory(process_units=[upstream_choke, *solver.get_recirculation_loops()])
    outlet = process_system.propagate_stream(inlet_stream=inlet_stream)

    assert outlet.pressure_bara == target_pressure
