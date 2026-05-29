import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.shaft import VariableSpeedShaft


def _chart(chart_data_factory, *, q0, min_rate_factor, max_rate_factor, head_hi, head_lo):
    return chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[q0 * min_rate_factor, q0 * max_rate_factor],
                polytropic_head_joule_per_kg=[head_hi, head_lo],
                efficiency_fraction=[0.75, 0.75],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[q0 * min_rate_factor, q0 * max_rate_factor],
                polytropic_head_joule_per_kg=[head_hi * 1.05, head_lo * 1.05],
                efficiency_fraction=[0.75, 0.75],
            ),
        ],
        control_margin=0.0,
    )


def test_individual_asv_rate_via_outlet_pressure_solver_two_stages(
    stream_factory,
    chart_data_factory,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_pipeline_factory,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    temperature = 300.0
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    stage1_chart = _chart(
        chart_data_factory, q0=q0, min_rate_factor=1.5, max_rate_factor=10.0, head_hi=80_000.0, head_lo=40_000.0
    )
    stage2_chart = _chart(
        chart_data_factory, q0=q0, min_rate_factor=1.2, max_rate_factor=6.0, head_hi=60_000.0, head_lo=30_000.0
    )

    shaft = VariableSpeedShaft()
    compressor1 = compressor_factory(chart_data=stage1_chart)
    compressor2 = compressor_factory(chart_data=stage2_chart)
    units1 = stage_units_factory(compressor=compressor1, shaft=shaft, temperature_kelvin=temperature)
    units2 = stage_units_factory(compressor=compressor2, shaft=shaft, temperature_kelvin=temperature)

    compressors = [compressor1, compressor2]
    wrapped_units, loops = with_individual_asv([*units1, *units2])
    loop_ids = [loop.get_id() for loop in loops]

    pipeline = process_pipeline_factory(units=wrapped_units)
    runner = process_runner_factory(units=wrapped_units, configuration_handlers=[shaft, *loops])
    anti_surge_strategy = individual_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_ids=loop_ids,
        compressors=compressors,
    )
    pressure_control_strategy = individual_asv_rate_control_strategy_factory(
        runner=runner,
        recirculation_loop_ids=loop_ids,
        compressors=compressors,
    )
    solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        process_pipeline_id=pipeline.get_id(),
    )

    target_pressure_bara = 70.0
    solution = solver.find_solution(
        pressure_constraint=FloatConstraint(target_pressure_bara),
        inlet_stream=inlet_stream,
    )

    assert solution.success is True

    runner.apply_configurations(solution.configuration)
    outlet = runner.run(inlet_stream=inlet_stream)
    assert outlet.pressure_bara == pytest.approx(target_pressure_bara, rel=1e-3)
