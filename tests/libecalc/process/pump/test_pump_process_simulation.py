import pytest

from libecalc.domain.process.value_objects.chart.chart import ChartCurve
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump
from libecalc.process.pump.pump_process_simulation import (
    LiquidProcessUnitType,
    PumpOperatingInput,
    PumpProcessSimulation,
)

DENSITY = 1021.0
CHART_MIN_FLOW = 277.0
MINIMUM_FLOW = 400.0


@pytest.fixture
def single_speed_chart(chart_data_factory):
    return chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=1,
                rate_actual_m3_hour=[277.0, 524.0, 666.0, 832.0, 927.0],
                polytropic_head_joule_per_kg=[10415.277, 9845.316, 9254.754, 8308.089, 7605.693],
                efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.6908],
            )
        ]
    )


@pytest.fixture
def simulation(single_speed_chart):
    return PumpProcessSimulation(
        pump=Pump(pump_chart=single_speed_chart, minimum_flow_rate_m3_per_hour=MINIMUM_FLOW),
        name="water_injection",
    )


def _operating_input(rate_m3_per_hour, *, discharge=100.0):
    return PumpOperatingInput(
        inlet_stream=LiquidStream.from_volumetric_rate(
            volumetric_rate_m3_per_day=rate_m3_per_hour * 24.0,
            pressure_bara=5.0,
            density_kg_per_m3=DENSITY,
        ),
        required_discharge_pressure_bara=discharge,
    )


def test_exposes_pump_static_data(simulation, single_speed_chart):
    # A consumer persists/renders the pump node from the simulation's static data.
    assert simulation.get_pump_chart().chart_data is single_speed_chart
    assert simulation.get_minimum_flow_rate_m3_per_hour() == MINIMUM_FLOW


def test_graph_structure(simulation):
    units = simulation.get_process_units()
    assert [unit.unit_type for unit in units] == [
        LiquidProcessUnitType.INLET,
        LiquidProcessUnitType.DIRECT_MIXER,
        LiquidProcessUnitType.PUMP,
        LiquidProcessUnitType.DIRECT_SPLITTER,
        LiquidProcessUnitType.CHOKE,
        LiquidProcessUnitType.OUTLET,
    ]

    # Connections form a serial chain: each connection starts at the previous unit's end.
    connections = simulation.get_process_unit_connections()
    assert len(connections) == 5
    for previous, current in zip(connections, connections[1:], strict=False):
        assert previous.get_to_process_unit_id() == current.get_from_process_unit_id()
    assert connections[0].get_from_process_unit_id() == units[0].get_id()
    assert connections[-1].get_to_process_unit_id() == units[-1].get_id()

    # The recirculation loop routes the splitter back to the mixer.
    loop = simulation.get_recirculation_loop()
    splitter = next(unit for unit in units if unit.unit_type is LiquidProcessUnitType.DIRECT_SPLITTER)
    mixer = next(unit for unit in units if unit.unit_type is LiquidProcessUnitType.DIRECT_MIXER)
    assert loop.splitter_id == splitter.get_id()
    assert loop.mixer_id == mixer.get_id()


def test_streams_projected_onto_every_connection(simulation):
    (result,) = simulation.evaluate([_operating_input(600.0)])

    connections = simulation.get_process_unit_connections()
    assert set(result.connection_streams) == {connection.get_id() for connection in connections}

    inlet_to_mixer = result.connection_streams[connections[0].get_id()]
    mixer_to_pump = result.connection_streams[connections[1].get_id()]
    pump_to_splitter = result.connection_streams[connections[2].get_id()]
    choke_to_outlet = result.connection_streams[connections[4].get_id()]

    pump_result = result.pump_result
    # Requested rate at suction on the inlet edge; operating rate at suction into the pump.
    assert inlet_to_mixer.volumetric_rate_m3_per_hour == pytest.approx(600.0)
    assert mixer_to_pump.volumetric_rate_m3_per_hour == pytest.approx(
        pump_result.operational_volumetric_rate_m3_per_hour
    )
    # The pump raises pressure; the choke drops it back toward the required discharge.
    assert pump_to_splitter.pressure_bara == pytest.approx(pump_result.operational_discharge_pressure_bara)
    assert choke_to_outlet.pressure_bara <= pump_to_splitter.pressure_bara
    assert choke_to_outlet.pressure_bara == pytest.approx(
        min(pump_result.operational_discharge_pressure_bara, pump_result.required_discharge_pressure_bara)
    )


def test_recirculation_raises_operating_flow_between_mixer_and_splitter(simulation):
    # Requested rate below the minimum flow -> the pump recirculates up to the minimum.
    (result,) = simulation.evaluate([_operating_input(300.0)])

    connections = simulation.get_process_unit_connections()
    inlet_to_mixer = result.connection_streams[connections[0].get_id()]
    mixer_to_pump = result.connection_streams[connections[1].get_id()]

    assert result.pump_result.recirculation_rate_m3_per_hour > 0.0
    assert mixer_to_pump.mass_rate_kg_per_h > inlet_to_mixer.mass_rate_kg_per_h


def test_zero_rate_produces_zero_result_at_inlet_pressure(simulation):
    # Pump off (rate 0): still a full result - zero power, outlet = inlet pressure, zero-flow streams.
    (result,) = simulation.evaluate([_operating_input(0.0, discharge=200.0)])

    assert result.pump_result.shaft_power_mw == 0.0
    assert result.pump_result.operational_discharge_pressure_bara == pytest.approx(5.0)

    connections = simulation.get_process_unit_connections()
    assert set(result.connection_streams) == {connection.get_id() for connection in connections}
    for stream in result.connection_streams.values():
        assert stream.mass_rate_kg_per_h == pytest.approx(0.0)


def test_evaluate_preserves_input_order(simulation):
    # The domain is time-agnostic: results come back in the same order as the inputs.
    results = simulation.evaluate([_operating_input(600.0), _operating_input(300.0), _operating_input(0.0)])
    assert len(results) == 3
    assert results[0].pump_result.recirculation_rate_m3_per_hour == pytest.approx(0.0)
    assert results[1].pump_result.recirculation_rate_m3_per_hour > 0.0
    assert results[2].pump_result.shaft_power_mw == 0.0
