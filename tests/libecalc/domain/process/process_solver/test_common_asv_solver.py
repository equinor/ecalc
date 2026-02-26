import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.common_asv_solver import CommonASVSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint


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

    common_asv_solver = CommonASVSolver(
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
    )

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature
    )
    assert inlet_stream.volumetric_rate_m3_per_hour == snapshot(681.2529349883239)

    speed_solution, recirculation_solution = common_asv_solver.find_common_asv_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )

    recirculation_loop = common_asv_solver.get_recirculation_loop()
    shaft.set_speed(speed_solution.configuration.speed)

    recirculation_at_capacity_solution = common_asv_solver.get_recirculation_solver(
        common_asv_solver.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream)
    ).solve(common_asv_solver.get_recirculation_func(inlet_stream=inlet_stream))

    assert speed_solution.success
    assert speed_solution.configuration.speed == snapshot(94.38349228734866)
    assert recirculation_solution.success

    recirculation_rate_at_capacity = recirculation_at_capacity_solution.configuration.recirculation_rate
    recirculation_rate_after_pressure_control = recirculation_solution.configuration.recirculation_rate

    assert recirculation_rate_at_capacity == snapshot(335543.7583238268)
    assert recirculation_rate_after_pressure_control >= recirculation_rate_at_capacity

    recirculation_loop.set_recirculation_rate(recirculation_solution.configuration.recirculation_rate)
    outlet_stream = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == target_pressure
