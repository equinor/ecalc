"""Regression: InfeasiblePressureError from a PressureDropper / Choke must
not propagate out of OutletPressureSolver."""

import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import InfeasiblePressureFailure
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.pressure_dropper import PressureDropper
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def single_speed_compressor(fluid_service):
    chart_data = ChartDataFactory.from_curves(
        [
            ChartCurve(
                rate_actual_m3_hour=[500.0, 1500.0],
                polytropic_head_joule_per_kg=[70000.0, 50000.0],
                efficiency_fraction=[0.75, 0.75],
                speed_rpm=100.0,
            )
        ]
    )
    return Compressor(
        compressor_chart=chart_data,
        fluid_service=fluid_service,
    )


def test_outlet_pressure_solver_handles_infeasible_pressure_from_pressure_dropper(
    stream_factory,
    fluid_service,
    single_speed_compressor,
    process_pipeline_factory,
    process_runner_factory,
    with_common_asv,
    common_asv_anti_surge_strategy_factory,
    downstream_choke_pressure_control_strategy_factory,
    choke_factory,
    choke_configuration_handler_factory,
    outlet_pressure_solver_factory,
):
    compressor = single_speed_compressor
    shaft = VariableSpeedShaft()
    shaft.connect(compressor)

    inlet_pressure = 25.0
    misconfigured_dropper = PressureDropper(
        fluid_service=fluid_service,
        pressure_drop_bara=inlet_pressure + 50.0,
    )

    downstream_choke = choke_factory()
    downstream_choke_handler = choke_configuration_handler_factory(choke=downstream_choke)

    recirculation_loop, looped_units = with_common_asv([compressor])
    units = [misconfigured_dropper, *looped_units, downstream_choke]
    runner = process_runner_factory(
        units=units,
        configuration_handlers=[shaft, recirculation_loop, downstream_choke_handler],
    )
    pipeline = process_pipeline_factory(units=units)
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=recirculation_loop.get_id(),
        first_compressor=compressor,
    )
    pressure_control_strategy = downstream_choke_pressure_control_strategy_factory(
        runner=runner,
        choke_id=downstream_choke_handler.get_id(),
    )
    solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        process_pipeline_id=pipeline.get_id(),
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=500_000, pressure_bara=inlet_pressure)

    solution = solver.find_solution(
        pressure_constraint=FloatConstraint(40.0),
        inlet_stream=inlet_stream,
    )

    assert solution.success is False
    assert isinstance(solution.failure, InfeasiblePressureFailure)
    assert solution.failure.source_id == misconfigured_dropper.get_id()
    assert solution.failure.achieved_pressure_bara is not None
    assert solution.failure.achieved_pressure_bara < 0.0
