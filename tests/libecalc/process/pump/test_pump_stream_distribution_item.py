import pytest

from libecalc.common.units import UnitConstants
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.stream_distribution.pump_stream_distribution_item import PumpStreamDistributionItem
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3


@pytest.mark.parametrize(
    "second_requested_outlet_pressure, is_valid",
    [
        # The second pump's suction pressure is the first pump's requested outlet pressure of 60 bara, and
        # the chart's head at 600 m3/h is 80 bar.
        pytest.param(120.0, True, id="both pumps within the chart"),
        pytest.param(150.0, False, id="second pump above the maximum head"),
    ],
)
def test_pipeline_is_valid_when_every_pump_problem_is(
    make_pump_pipeline_runtime, single_speed_chart, second_requested_outlet_pressure, is_valid
):
    pipeline = make_pump_pipeline_runtime(single_speed_chart, has_choke=[True, True])
    item = PumpStreamDistributionItem(
        pipeline.solver, requested_outlet_pressures_bara=[60.0, second_requested_outlet_pressure]
    )
    inlet_stream = LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=600.0 * UnitConstants.HOURS_PER_DAY,
        pressure_bara=10.0,
        density_kg_per_m3=DENSITY_KG_PER_M3,
    )

    first_solution, second_solution = item.find_solutions(inlet_stream)

    assert first_solution.is_valid
    assert second_solution.is_valid is is_valid
    assert item.is_valid(inlet_stream) is is_valid
