import itertools

import pytest

from libecalc.common.units import UnitConstants
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3

# The single-speed chart has a head of 80 bar at 600 m3/h. The variable-speed chart has 80 to 170 bar there.
INLET_PRESSURE = 10.0
RELATIVE_TOLERANCE = 1e-9


def _inlet_stream(rate_m3_per_hour: float, pressure_bara: float = INLET_PRESSURE) -> LiquidStream:
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * UnitConstants.HOURS_PER_DAY,
        pressure_bara=pressure_bara,
        density_kg_per_m3=DENSITY_KG_PER_M3,
    )


@pytest.mark.parametrize("has_choke", [True, False], ids=["with a choke", "without a choke"])
@pytest.mark.parametrize("chart_name", ["single_speed_chart", "variable_speed_chart"])
def test_streams_reproduce_pump_evaluate(request, make_pump_pipeline_runtime, chart_name, has_choke):
    """The rates and the pressures cover a stopped pump, recirculation, both sides of the chart's head range
    and a rate above the chart's maximum rate."""
    pipeline = make_pump_pipeline_runtime(request.getfixturevalue(chart_name), has_choke=[has_choke])
    [problem] = pipeline.problems
    [problem_solver] = pipeline.problem_solvers

    for rate, inlet_pressure, requested_outlet_pressure in itertools.product(
        [0.0, 100.0, 250.0, 600.0, 1000.0, 1300.0], [5.3, 10.0], [50.0, 90.0, 128.2, 142.5, 180.0, 200.0]
    ):
        point = f"{rate} m3/h from {inlet_pressure} bara to {requested_outlet_pressure} bara"
        inlet_stream = _inlet_stream(rate, inlet_pressure)

        solution = problem_solver.find_solution(inlet_stream, requested_outlet_pressure)
        streams = pipeline.runner.run_to_each_unit(inlet_stream)

        pump_result = solution.pump_result
        assert pump_result == problem.pump.evaluate(inlet_stream, requested_outlet_pressure), point
        assert [configuration.configuration_handler_id for configuration in solution.configurations] == [
            handler.get_id() for handler in problem.get_configuration_handlers()
        ], point

        into_pump = streams[problem.pump.get_id()]
        into_splitter = streams[problem.splitter.get_id()]
        into_outlet = streams[pipeline.outlet.get_id()]
        operational_rate = pytest.approx(pump_result.operational_volumetric_rate_m3_per_hour, rel=RELATIVE_TOLERANCE)
        assert into_pump.volumetric_rate_m3_per_hour == operational_rate, point
        assert into_pump.pressure_bara == inlet_pressure, point
        assert into_splitter.volumetric_rate_m3_per_hour == operational_rate, point
        assert into_splitter.pressure_bara == pytest.approx(
            pump_result.operational_discharge_pressure_bara, rel=RELATIVE_TOLERANCE
        ), point
        assert into_outlet.volumetric_rate_m3_per_hour == pytest.approx(rate, rel=RELATIVE_TOLERANCE), point
        assert into_outlet.pressure_bara == pytest.approx(
            pump_result.operational_outlet_pressure_bara
            if has_choke
            else pump_result.operational_discharge_pressure_bara,
            rel=RELATIVE_TOLERANCE,
        ), point


@pytest.mark.parametrize(
    "chart_name, has_choke, rate, requested_outlet_pressure, is_above_requested, is_valid, outlet_pressure",
    [
        pytest.param(
            "single_speed_chart", False, 600.0, 60.0, True, False, 90.0, id="the chart's minimum head, no choke"
        ),
        pytest.param(
            "single_speed_chart", True, 600.0, 60.0, False, True, 60.0, id="the chart's minimum head, with a choke"
        ),
        pytest.param("variable_speed_chart", False, 600.0, 135.0, False, True, 135.0, id="inside the chart, no choke"),
        pytest.param(
            "single_speed_chart", False, 600.0, 100.0, False, False, 90.0, id="above the maximum head, no choke"
        ),
        # A stopped pump has an operational head of zero, which is above a negative required head.
        pytest.param(
            "single_speed_chart", False, 0.0, 8.0, False, True, INLET_PRESSURE, id="stopped below its suction pressure"
        ),
    ],
)
def test_problem_without_a_choke_is_not_valid_when_its_pump_is_above_the_requested_outlet_pressure(
    request,
    make_pump_pipeline_runtime,
    chart_name,
    has_choke,
    rate,
    requested_outlet_pressure,
    is_above_requested,
    is_valid,
    outlet_pressure,
):
    pipeline = make_pump_pipeline_runtime(request.getfixturevalue(chart_name), has_choke=[has_choke])
    [problem_solver] = pipeline.problem_solvers
    inlet_stream = _inlet_stream(rate)

    solution = problem_solver.find_solution(inlet_stream, requested_outlet_pressure)

    assert solution.outlet_pressure_above_requested is is_above_requested
    assert solution.is_valid is is_valid
    assert pipeline.runner.run(inlet_stream).pressure_bara == pytest.approx(outlet_pressure)


def test_pump_inside_its_chart_is_not_above_the_requested_outlet_pressure_by_rounding(
    make_pump_pipeline_runtime, variable_speed_chart
):
    pipeline = make_pump_pipeline_runtime(variable_speed_chart, has_choke=[False])
    [problem_solver] = pipeline.problem_solvers
    inlet_stream = _inlet_stream(600.0, pressure_bara=5.3)
    requested_outlet_pressures = [128.2, 128.7, 129.2]

    solutions = [
        problem_solver.find_solution(inlet_stream, requested_outlet_pressure)
        for requested_outlet_pressure in requested_outlet_pressures
    ]

    # The discharge pressure is computed back from the head, and it is above the requested one in the last
    # digit.
    for solution, requested_outlet_pressure in zip(solutions, requested_outlet_pressures, strict=True):
        discharge_pressure = solution.pump_result.operational_discharge_pressure_bara
        assert discharge_pressure > requested_outlet_pressure
        assert discharge_pressure == pytest.approx(requested_outlet_pressure, rel=RELATIVE_TOLERANCE)
        assert not solution.outlet_pressure_above_requested
        assert solution.is_valid
