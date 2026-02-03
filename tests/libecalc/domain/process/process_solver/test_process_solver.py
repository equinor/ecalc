import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.process_solver import (
    ProcessSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.domain.process.value_objects.chart.chart import ChartData


@pytest.fixture
def chart_data(chart_data_factory) -> ChartData:
    return chart_data_factory.from_design_point(1000, 60_000, 0.7)


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.mark.snapshot
@pytest.mark.inlinesnapshot
def test_speed_solver(
    search_strategy_factory,
    root_finding_strategy,
    fluid_service,
    stream_factory,
    process_system_factory,
    stream_constraint_factory,
    chart_data,
    compressor_train_stage_process_unit_factory,
    shaft,
):
    chart_speeds = [curve.speed for curve in chart_data.get_adjusted_curves()]
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target_pressure = 90
    stream_constraint = stream_constraint_factory(pressure=target_pressure)
    process_system = process_system_factory(
        process_units=[compressor_train_stage_process_unit_factory(chart_data=chart_data, shaft=shaft)],
    )

    process_solver = ProcessSolver(
        inlet_stream=inlet_stream,
        process_system=process_system,
        solvers=[
            SpeedSolver(
                search_strategy=search_strategy_factory(),
                root_finding_strategy=root_finding_strategy,
                target_pressure=target_pressure,
                boundary=Boundary(min=min(chart_speeds), max=max(chart_speeds)),
                shaft=shaft,
            ),
        ],
        stream_constraint=stream_constraint,
    )
    assert process_solver.find_solution()
    assert shaft.get_speed() == snapshot(102.66555959304989)

    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == pytest.approx(target_pressure)
    assert outlet_stream.standard_rate_sm3_per_day == pytest.approx(1000)
