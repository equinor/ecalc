import pytest

from libecalc.common.units import UnitConstants
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3

BOOSTER_REQUESTED_OUTLET_PRESSURE = 60.0
MAIN_REQUESTED_OUTLET_PRESSURE = 120.0
PRESSURE_DROP_BETWEEN_THE_PUMPS = 2.0


def _inlet_stream(rate_m3_per_hour: float, pressure_bara: float) -> LiquidStream:
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * UnitConstants.HOURS_PER_DAY,
        pressure_bara=pressure_bara,
        density_kg_per_m3=DENSITY_KG_PER_M3,
    )


def test_every_call_solves_the_pump_problems_in_flow_order_for_its_own_inlet_stream(
    make_pump_pipeline_runtime, single_speed_chart
):
    """A booster and a main pump, each with a choke, and a pressure dropper between them.

    The chart's head is 80 bar at 600 m3/h and 90 bar at its minimum rate of 200 m3/h. The streams are those
    into the inlet, the booster's mixer, pump, splitter and choke, the pressure dropper, the main pump's
    mixer, pump, splitter and choke, and the outlet.
    """
    pipeline = make_pump_pipeline_runtime(
        single_speed_chart,
        has_choke=[True, True],
        upstream_pressure_drops_bara=[None, PRESSURE_DROP_BETWEEN_THE_PUMPS],
    )
    booster, main = pipeline.problems
    running = (
        _inlet_stream(rate_m3_per_hour=600.0, pressure_bara=10.0),
        [600.0] * 11,
        [10.0, 10.0, 10.0, 90.0, 90.0, 60.0, 58.0, 58.0, 138.0, 138.0, 120.0],
    )
    recirculating = (
        _inlet_stream(rate_m3_per_hour=100.0, pressure_bara=20.0),
        [100.0, 100.0, 200.0, 200.0, 100.0, 100.0, 100.0, 200.0, 200.0, 100.0, 100.0],
        [20.0, 20.0, 20.0, 110.0, 110.0, 60.0, 58.0, 58.0, 148.0, 148.0, 120.0],
    )
    stopped = (_inlet_stream(rate_m3_per_hour=0.0, pressure_bara=10.0), [0.0] * 11, [10.0] * 11)

    for inlet_stream, rates_m3_per_hour, pressures_bara in (running, recirculating, stopped, running):
        solutions = pipeline.solver.find_solutions(
            inlet_stream, [BOOSTER_REQUESTED_OUTLET_PRESSURE, MAIN_REQUESTED_OUTLET_PRESSURE]
        )
        streams = list(pipeline.runner.run_to_each_unit(inlet_stream).values())

        assert [solution.pump_result.process_unit_id for solution in solutions] == [
            booster.pump.get_id(),
            main.pump.get_id(),
        ]
        assert [stream.volumetric_rate_m3_per_hour for stream in streams] == pytest.approx(rates_m3_per_hour)
        assert [stream.pressure_bara for stream in streams] == pytest.approx(pressures_bara)
