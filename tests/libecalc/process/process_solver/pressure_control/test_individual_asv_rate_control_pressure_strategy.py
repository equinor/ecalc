import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.shaft import VariableSpeedShaft


@pytest.mark.parametrize("target_pressure_bara", [50.0, 70.0, 87.0])
def test_individual_asv_rate_control_reaches_target_pressure(
    target_pressure_bara,
    stream_factory,
    chart_data_factory,
    fluid_service,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_rate_control_strategy_factory,
):
    """IndividualASVRateControlStrategy must converge to the target pressure."""
    temperature = 300.0
    inlet_standard_rate = 500_000.0  # sm3/day
    inlet_pressure = 30.0  # bara

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=inlet_standard_rate,
        pressure_bara=inlet_pressure,
        temperature_kelvin=temperature,
    )
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # min_rate=2*q0 ensures the inlet is always below the surge line, so ASV is required.
    # Targets 50, 70, 87 are chosen to lie strictly between the max-recirc outlet (~41 bara)
    # and the surge-point outlet (~89 bara).
    chart_data = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[q0 * 2, q0 * 8],
                polytropic_head_joule_per_kg=[150_000.0, 40_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[q0 * 2, q0 * 8],
                polytropic_head_joule_per_kg=[150_000.0 * 1.05, 40_000.0 * 1.05],
                efficiency_fraction=[0.75, 0.75],
            ),
        ],
        control_margin=0.0,
    )

    shaft = VariableSpeedShaft()
    compressor = compressor_factory(chart_data=chart_data)
    units = stage_units_factory(compressor=compressor, shaft=shaft, temperature_kelvin=temperature)
    shaft.set_speed(75.0)

    compressors = [compressor]
    wrapped_units, loops = with_individual_asv(units)
    loop_ids = [loop.get_id() for loop in loops]
    runner = process_runner_factory(units=wrapped_units, configuration_handlers=[shaft, *loops])

    strategy = individual_asv_rate_control_strategy_factory(
        runner=runner,
        recirculation_loop_ids=loop_ids,
        compressors=compressors,
    )

    target = FloatConstraint(target_pressure_bara)
    solution = strategy.apply(target_pressure=target, inlet_stream=inlet_stream)

    assert solution.success is True

    runner.apply_configurations(solution.configuration)
    outlet = runner.run(inlet_stream=inlet_stream)

    assert outlet.pressure_bara == pytest.approx(target_pressure_bara, rel=1e-3)
