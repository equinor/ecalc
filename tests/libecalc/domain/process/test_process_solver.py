import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.process_units.choke import Choke
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
        shaft=shaft,
        process_units=[compressor_train_stage_process_unit_factory(chart_data=chart_data, shaft=shaft)],
        downstream_choke=Choke(fluid_service=fluid_service),
    )

    process_solver = ProcessSolver(
        inlet_stream=inlet_stream,
        process_system=process_system,
        solvers=[
            SpeedSolver(
                target_pressure=target_pressure,
                boundary=Boundary(min=min(chart_speeds), max=max(chart_speeds)),
            ),
        ],
        stream_constraint=stream_constraint,
    )
    assert process_solver.find_solution()
    assert process_system.get_shaft().get_speed() == snapshot(98.8165960635718)

    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream.pressure_bara == pytest.approx(target_pressure)
    assert outlet_stream.standard_rate_sm3_per_day == pytest.approx(1000)
