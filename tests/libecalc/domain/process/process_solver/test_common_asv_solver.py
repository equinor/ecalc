import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_common_asv_solver(
    stream_factory,
    compressor_train_stage_process_unit_factory,
    root_finding_strategy,
    search_strategy_factory,
    shaft,
    fluid_service,
    chart_data_factory,
):
    target_pressure = FloatConstraint(75)
    temperature = 300

    stage1_chart_data = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
    stage2_chart_data = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

    common_asv_solver = ASVSolver(
        shaft=shaft,
        compressors=[
            compressor_train_stage_process_unit_factory(
                chart_data=stage1_chart_data,
                shaft=shaft,
                temperature_kelvin=temperature,
            ),
            compressor_train_stage_process_unit_factory(chart_data=stage2_chart_data, shaft=shaft),
        ],
        fluid_service=fluid_service,
        individual_asv_control=False,
    )

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature
    )
    assert inlet_stream.volumetric_rate_m3_per_hour == snapshot(681.2529349883239)

    solution = common_asv_solver.find_asv_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )
    config_dict = {config.simulation_unit_id: config.value for config in solution.configuration}

    speed_configuration = config_dict[shaft.get_id()]

    recirculation_at_capacity_solution = common_asv_solver.get_anti_surge_solution()

    # runner = common_asv_solver.get_runner()
    # runner.apply_configurations([
    #    Configuration(
    #        simulation_unit_id=shaft.get_id(),
    #        value=SpeedConfiguration(speed=94.40011432582548),
    #    ),
    #    Configuration(
    #        simulation_unit_id=common_asv_solver._recirculation_loops[0].get_id(),
    #        value=RecirculationConfiguration(recirculation_rate=336264.5247203157),
    #    )
    # ])
    # solution = runner.run(inlet_stream=inlet_stream)

    assert solution.success
    assert speed_configuration.speed == snapshot(94.40011432582548)

    recirculation_rate_at_capacity = recirculation_at_capacity_solution.configuration[0].value.recirculation_rate

    recirculation_configuration = [
        config for config in solution.configuration if isinstance(config.value, RecirculationConfiguration)
    ][0]
    recirculation_rate_after_pressure_control = recirculation_configuration.value.recirculation_rate

    assert recirculation_rate_at_capacity == snapshot(336264.5247203157)
    assert recirculation_rate_after_pressure_control >= recirculation_rate_at_capacity

    runner = common_asv_solver.get_runner()
    runner.apply_configurations(solution.configuration)
    outlet_stream = runner.run(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == target_pressure
