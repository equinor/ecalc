from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint


def test_asv_solver_applies_downstream_choke_when_speed_solution_is_at_min_speed(
    stream_factory,
    process_system_factory,
    fluid_service,
    choke_factory,
    speed_compressor_stage_factory,
):
    """
    If the target outlet pressure is lower than the outlet pressure at minimum speed, SpeedSolver returns
    success=False and selects the minimum speed. ASVSolver should still attempt pressure control, and with a
    downstream choke it should be able to meet the target.
    """
    shaft = VariableSpeedShaft()
    downstream_choke = choke_factory()

    # One "compressor" stage that increases pressure with speed, followed by a downstream choke.
    compressor = speed_compressor_stage_factory(shaft=shaft)

    solver = ASVSolver(
        shaft=shaft,
        compressors=[compressor],
        fluid_service=fluid_service,
        individual_asv_control=False,
        downstream_choke=downstream_choke,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=25.0)

    # At min speed=200 => baseline outlet = 25 + 200 = 225.
    # Choose a target lower than 225 so SpeedSolver returns min speed with success=False.
    target_pressure = FloatConstraint(50.0, abs_tol=1e-12)

    solution = solver.find_asv_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )
    config_dict = {configuration.simulation_unit_id: configuration.value for configuration in solution.configuration}
    speed_configuration = config_dict[shaft.get_id()]

    # SpeedSolver could not meet the target pressure within the speed boundary,
    # so it returned the minimum speed as the best feasible speed.
    assert speed_configuration.speed == compressor.get_speed_boundary().min

    # But overall solver should succeed via downstream choke pressure control.
    assert solution.success
    assert config_dict[downstream_choke.get_id()].delta_pressure > 0

    # Verify that downstream choking actually brings outlet down to target.
    # Build the same top-level process system that downstream choke runner uses:
    # recirc loops (1) + choke
    runner = solver.get_runner()
    runner.apply_configurations(solution.configuration)
    outlet = runner.run(inlet_stream=inlet_stream)
    assert outlet.pressure_bara == target_pressure
