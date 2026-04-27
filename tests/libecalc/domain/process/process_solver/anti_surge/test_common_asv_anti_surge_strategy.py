import pytest

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.value_objects.chart import ChartCurve


def test_common_asv_anti_surge_uses_compressor_inlet_for_boundary(
    stream_factory,
    chart_data_factory,
    fluid_service,
    compressor_factory,
    stage_units_factory,
    with_common_asv,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
):
    """
    COMMON ASV anti-surge must compute the recirculation boundary on the compressor-inlet
    stream (after TemperatureSetter / Choke / LiquidRemover), not the train-inlet stream.

    A TemperatureSetter is placed before the compressor so the two streams differ measurably,
    making it observable which one the strategy uses.
    """

    # Two clearly different temperatures, so train-inlet and compressor-inlet streams
    # produce different densities — and therefore different boundaries.
    train_inlet_temperature_kelvin = 280.0  # train inlet
    stage_inlet_temperature_kelvin = 320.0  # enforced by TemperatureSetter

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=train_inlet_temperature_kelvin,
    )
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # Wide chart so boundary.min/max are non-degenerate; otherwise the strategy
    # would short-circuit and never query get_recirculation_range meaningfully.
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
    compressor = compressor_factory(chart_data=chart_data)
    units = stage_units_factory(
        compressor=compressor,
        shaft=shaft,
        temperature_kelvin=stage_inlet_temperature_kelvin,
    )
    shaft.set_speed(75.0)

    recirculation_loop, wrapped_units = with_common_asv(units)
    runner = process_runner_factory(units=wrapped_units, configuration_handlers=[shaft, recirculation_loop])

    strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=recirculation_loop.get_id(),
        first_compressor=compressor,
    )

    # Compute both candidate boundaries independently, to verify difference
    boundary_on_train_inlet = compressor.get_recirculation_range(inlet_stream)
    compressor_inlet = runner.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
    boundary_on_compressor_inlet = compressor.get_recirculation_range(compressor_inlet)

    # Sanity: TemperatureSetter actually changed the stream the compressor sees.
    assert inlet_stream.temperature_kelvin != compressor_inlet.temperature_kelvin
    # Sanity: the two candidate boundaries differ.
    assert boundary_on_train_inlet.min != pytest.approx(boundary_on_compressor_inlet.min, rel=1e-3)

    # Capture the stream that the strategy passes into get_recirculation_range.
    captured_streams = []
    original = compressor.get_recirculation_range

    def spy(inlet_stream):
        captured_streams.append(inlet_stream)
        return original(inlet_stream)

    compressor.get_recirculation_range = spy

    # Trigger the strategy. Anti-surge calls get_recirculation_range as the very
    # first step inside apply(), so we just need to invoke it.
    strategy.apply(inlet_stream=inlet_stream)

    # Verify the strategy used the compressor-inlet stream, not the train-inlet stream.
    assert captured_streams, "Strategy never queried get_recirculation_range"
    used_stream = captured_streams[0]
    assert used_stream.temperature_kelvin == pytest.approx(stage_inlet_temperature_kelvin), (
        f"Strategy used stream at T={used_stream.temperature_kelvin:.1f} K for boundary; "
        f"expected compressor-inlet stream at T={stage_inlet_temperature_kelvin:.1f} K "
        f"(train-inlet was T={train_inlet_temperature_kelvin:.1f} K)."
    )
