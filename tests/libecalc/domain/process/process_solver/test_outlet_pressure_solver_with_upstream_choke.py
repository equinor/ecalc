import pytest

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def single_speed_compressor(fluid_service):
    """Single-speed compressor with a two-point chart, for simple choke solver tests."""
    chart_data = ChartDataFactory.from_curves(
        [
            ChartCurve(
                rate_actual_m3_hour=[500.0, 1500.0],
                polytropic_head_joule_per_kg=[70000.0, 50000.0],
                efficiency_fraction=[0.75, 0.75],
                speed_rpm=100.0,
            )
        ]
    )
    return Compressor(
        process_unit_id=create_process_unit_id(),
        compressor_chart=chart_data,
        fluid_service=fluid_service,
    )


def test_outlet_pressure_solver_applies_upstream_choke_when_speed_solution_is_at_min_speed(
    stream_factory,
    process_system_factory,
    choke_factory,
    single_speed_compressor,
    recirculation_loop_factory,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    upstream_choke_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    """
    If the outlet pressure is higher than the target outlet pressure at minimum speed, SpeedSolver returns
    success=False and selects the minimum speed. CommonSpeedWithPressureControlSolver should still attempt pressure control, and with an
    upstream choke it should be able to meet the target.
    """
    compressor = single_speed_compressor
    shaft = VariableSpeedShaft()
    shaft.connect(compressor)
    upstream_choke = choke_factory()

    common_asv = recirculation_loop_factory(inner_process=process_system_factory(process_units=[compressor]))
    runner = process_runner_factory(units=[upstream_choke, common_asv], shaft=shaft)
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=common_asv.get_id(),
        first_compressor=compressor,
    )
    pressure_control_strategy = upstream_choke_pressure_control_strategy_factory(
        runner=runner,
        choke_id=upstream_choke.get_id(),
    )
    solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
    )

    # 500_000 sm3/day at 25 bara gives ~850 m3/h actual, which fits within [500, 1500].
    inlet_stream = stream_factory(standard_rate_m3_per_day=500_000, pressure_bara=25.0)

    # The compressor (single speed) produces outlet pressure well above 28 bara.
    # SpeedSolver cannot lower it further, so it returns min speed with success=False.
    # The upstream choke reduces inlet pressure, which lowers outlet pressure to the target.
    target_pressure = FloatConstraint(28.0, abs_tol=1e-4)

    solution = solver.find_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )
    config_dict = {config.simulation_unit_id: config.value for config in solution.configuration}

    speed_configuration = config_dict[shaft.get_id()]

    # Single-speed compressor: SpeedSolver is forced to return the only available speed.
    assert speed_configuration.speed == shaft.get_speed_boundary().min

    # Overall solver should succeed via upstream choke pressure control.
    assert solution.success
    assert config_dict[upstream_choke.get_id()].delta_pressure > 0

    # Verify that upstream choking actually brings outlet down to target.
    runner.apply_configurations(solution.configuration)
    outlet = runner.run(inlet_stream=inlet_stream)
    assert outlet.pressure_bara == target_pressure
