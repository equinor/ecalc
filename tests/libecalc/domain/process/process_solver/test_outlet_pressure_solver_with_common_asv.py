import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_outlet_pressure_solver_with_common_asv(
    stream_factory,
    compressor_train_stage_process_unit_factory,
    shaft,
    chart_data_factory,
    recirculation_loop_factory,
    process_system_factory,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    target_pressure = FloatConstraint(75)
    temperature = 300

    stage1_chart_data = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
    stage2_chart_data = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

    stage1 = compressor_train_stage_process_unit_factory(
        chart_data=stage1_chart_data,
        shaft=shaft,
        temperature_kelvin=temperature,
    )
    stage2 = compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft)

    speed_boundaries = [stage1.get_speed_boundary(), stage2.get_speed_boundary()]
    speed_boundary = Boundary(
        min=max(b.min for b in speed_boundaries),
        max=min(b.max for b in speed_boundaries),
    )

    common_asv = recirculation_loop_factory(inner_process=process_system_factory(process_units=[stage1, stage2]))
    runner = process_runner_factory(units=[common_asv], shaft=shaft)
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=common_asv.get_id(),
        first_compressor=stage1,
    )
    pressure_control_strategy = common_asv_pressure_control_strategy_factory(
        runner=runner,
        recirculation_loop_id=common_asv.get_id(),
        first_compressor=stage1,
    )
    common_asv_solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        speed_boundary=speed_boundary,
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
    assert speed_configuration.speed == snapshot(94.40011432582548)

    recirculation_rate_at_capacity = recirculation_at_capacity_solution.configuration[0].value.recirculation_rate

    recirculation_configuration = [
        config for config in solution.configuration if isinstance(config.value, RecirculationConfiguration)
    ][0]
    recirculation_rate_after_pressure_control = recirculation_configuration.value.recirculation_rate

    assert recirculation_rate_at_capacity == snapshot(336264.5247203157)
    assert recirculation_rate_after_pressure_control >= recirculation_rate_at_capacity

    runner.apply_configurations(solution.configuration)
    outlet_stream = runner.run(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == target_pressure
