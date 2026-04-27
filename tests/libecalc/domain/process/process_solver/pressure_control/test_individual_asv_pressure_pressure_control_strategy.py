import pytest

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.value_objects.chart import ChartCurve


@pytest.mark.parametrize("target_pressure_bara", [50.0, 70.0, 87.0])
def test_individual_asv_pressure_control_reaches_target_pressure(
    target_pressure_bara,
    stream_factory,
    chart_data_factory,
    fluid_service,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_pressure_control_strategy_factory,
):
    """IndividualASVPressureControlStrategy must reach the target pressure and report success."""
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

    from libecalc.domain.process.entities.shaft import VariableSpeedShaft

    shaft = VariableSpeedShaft()
    compressor = compressor_factory(chart_data=chart_data)
    units = stage_units_factory(compressor=compressor, shaft=shaft, temperature_kelvin=temperature)
    shaft.set_speed(75.0)

    compressors = [compressor]
    wrapped_units, loops = with_individual_asv(units)
    loop_ids = [loop.get_id() for loop in loops]
    runner = process_runner_factory(units=wrapped_units, configuration_handlers=[shaft, *loops])

    strategy = individual_asv_pressure_control_strategy_factory(
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


def test_individual_asv_pressure_each_stage_meets_geometric_target(
    stream_factory,
    chart_data_factory,
    fluid_service,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_pressure_control_strategy_factory,
):
    """Each stage's outlet must equal inlet * ratio^(i+1), where ratio = (target/inlet)^(1/n).

    Per-stage solving must compare against the stage's own outlet, not the full train outlet —
    otherwise stage 0 over-recirculates to hit the train target alone (with downstream stages
    still at rate=0), leaving stage 0's outlet near the train target instead of the geometric
    midpoint.
    """

    # 2 stages is the minimum that exposes the per-stage solving contract:
    # with 1 stage, stage_target == train_target and the contract is trivially satisfied.
    n_stages = 2
    inlet_pressure = 30.0
    target_pressure_bara = 60.0  # ratio per stage = sqrt(2) ≈ 1.414, stage 0 outlet ≈ 42.4 bara

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=inlet_pressure,
        temperature_kelvin=300.0,
    )
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # Wide chart so the per-stage solver has room to find an interior solution
    # (not pinned to surge or stonewall).
    chart_data = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[q0 * 2, q0 * 8],
                polytropic_head_joule_per_kg=[150_000.0, 40_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
        ],
        control_margin=0.0,
    )

    shaft = VariableSpeedShaft()
    compressors = [compressor_factory(chart_data=chart_data) for _ in range(n_stages)]
    units = []
    for compressor in compressors:
        units.extend(stage_units_factory(compressor=compressor, shaft=shaft, temperature_kelvin=300.0))
    shaft.set_speed(75.0)

    wrapped_units, loops = with_individual_asv(units)
    runner = process_runner_factory(units=wrapped_units, configuration_handlers=[shaft, *loops])

    strategy = individual_asv_pressure_control_strategy_factory(
        runner=runner,
        recirculation_loop_ids=[loop.get_id() for loop in loops],
        compressors=compressors,
    )

    # Solve and apply the resulting per-loop recirculation rates.
    solution = strategy.apply(target_pressure=FloatConstraint(target_pressure_bara), inlet_stream=inlet_stream)
    assert solution.success is True
    runner.apply_configurations(solution.configuration)

    # Geometrically distributed targets: stage i outlet = inlet * ratio^(i+1).
    pressure_ratio_per_stage = (target_pressure_bara / inlet_pressure) ** (1.0 / n_stages)
    expected_outlet_pressures = [inlet_pressure * (pressure_ratio_per_stage ** (i + 1)) for i in range(n_stages)]

    # Read each stage's actual outlet by propagating up to the compressor and through it.
    actual_outlet_pressures = []
    for compressor in compressors:
        compressor_inlet = runner.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
        actual_outlet_pressures.append(compressor.propagate_stream(compressor_inlet).pressure_bara)

    # Each stage must match its own geometric target. Stage 0 in particular must land at
    # sqrt(inlet*target) — landing near the train target would indicate stage 0 is solving
    # against the full train outlet instead of its own.
    for i, (actual, expected) in enumerate(zip(actual_outlet_pressures, expected_outlet_pressures)):
        assert actual == pytest.approx(
            expected, rel=5e-3
        ), f"Stage {i} outlet {actual:.3f} bara != expected {expected:.3f} bara"
