import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_outlet_pressure_solver_with_common_asv(
    stream_factory,
    stage_units_factory,
    shaft,
    chart_data_factory,
    with_common_asv,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    target_pressure = FloatConstraint(75)
    temperature = 300

    stage1_chart_data = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
    stage2_chart_data = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

    stage1 = stage_units_factory(chart_data=stage1_chart_data, shaft=shaft, temperature_kelvin=temperature)
    stage2 = stage_units_factory(chart_data=stage2_chart_data, shaft=shaft)

    common_asv, loop_id, first_compressor = with_common_asv([*stage1, *stage2])
    runner = process_runner_factory(units=[common_asv], shaft=shaft)
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=loop_id,
        first_compressor=first_compressor,
    )
    pressure_control_strategy = common_asv_pressure_control_strategy_factory(
        runner=runner,
        recirculation_loop_id=loop_id,
        first_compressor=first_compressor,
    )
    common_asv_solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
    )

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature
    )
    assert inlet_stream.volumetric_rate_m3_per_hour == snapshot(681.2529349883239)

    solution = common_asv_solver.find_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )
    config_dict = {config.simulation_unit_id: config.value for config in solution.configuration}

    speed_configuration = config_dict[shaft.get_id()]

    recirculation_at_capacity_solution = common_asv_solver.get_anti_surge_solution()

    assert solution.success
    assert speed_configuration.speed == snapshot(94.40012312859398)

    recirculation_rate_at_capacity = recirculation_at_capacity_solution.configuration[0].value.recirculation_rate

    recirculation_configuration = [
        config for config in solution.configuration if isinstance(config.value, RecirculationConfiguration)
    ][0]
    recirculation_rate_after_pressure_control = recirculation_configuration.value.recirculation_rate

    assert recirculation_rate_at_capacity == snapshot(336264.90573204844)
    assert recirculation_rate_after_pressure_control >= recirculation_rate_at_capacity

    runner.apply_configurations(solution.configuration)
    outlet_stream = runner.run(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == target_pressure


@pytest.fixture
def small_chart_compressor(fluid_service, shaft):
    chart_data = ChartDataFactory.from_curves(
        [
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[50.0, 200.0],
                polytropic_head_joule_per_kg=[120_000.0, 80_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[70.0, 300.0],
                polytropic_head_joule_per_kg=[170_000.0, 110_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
        ]
    )
    compressor = Compressor(
        process_unit_id=create_process_unit_id(),
        compressor_chart=chart_data,
        fluid_service=fluid_service,
    )
    shaft.register(compressor)
    return compressor


def test_find_solution_returns_failure_when_rate_above_stonewall(
    shaft,
    small_chart_compressor,
    stream_factory,
    with_common_asv,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    common_asv, loop_id, first_compressor = with_common_asv([small_chart_compressor])

    runner = process_runner_factory(units=[common_asv], shaft=shaft)
    anti_surge = common_asv_anti_surge_strategy_factory(
        runner=runner, recirculation_loop_id=loop_id, first_compressor=first_compressor
    )
    pressure_control = common_asv_pressure_control_strategy_factory(
        runner=runner, recirculation_loop_id=loop_id, first_compressor=first_compressor
    )
    solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge,
        pressure_control_strategy=pressure_control,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=5_000_000, pressure_bara=30.0, temperature_kelvin=300.0)
    assert inlet_stream.volumetric_rate_m3_per_hour > 300.0

    solution = solver.find_solution(
        pressure_constraint=FloatConstraint(75.0),
        inlet_stream=inlet_stream,
    )

    assert not solution.success
