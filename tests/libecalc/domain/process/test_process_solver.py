from typing import TypeGuard

import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.choke import Choke
from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.process_solver import (
    ProcessSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.domain.process.process_solver.stream_constraint import StreamConstraint
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class StageProcessUnit(ProcessUnit):
    def __init__(self, compressor_stage: CompressorTrainStage):
        self._compressor_stage = compressor_stage

    def get_shaft(self) -> Shaft:
        return self._compressor_stage.compressor.shaft

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream | None:
        result = self._compressor_stage.evaluate(inlet_stream_stage=inlet_stream)
        return result.outlet_stream


@pytest.fixture
def process_system_factory(compressor_stage_factory, fluid_service):
    def create_process_system(chart_data: ChartData, downstream_choke: Choke | None = None):
        shaft = VariableSpeedShaft()
        return ProcessSystem(
            shaft=shaft,
            process_units=[
                StageProcessUnit(
                    compressor_stage=compressor_stage_factory(
                        compressor_chart_data=chart_data,
                        shaft=shaft,
                    )
                ),
            ],
            downstream_choke=downstream_choke,
        )

    return create_process_system


class PressureStreamConstraint(StreamConstraint):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]:
        if stream is None:
            return False
        # return stream.pressure_bara == self._target_pressure
        return self._target_pressure - EPSILON <= stream.pressure_bara <= self._target_pressure + EPSILON


@pytest.fixture
def stream_constraint_factory():
    def create_stream_constraint(pressure: float):
        return PressureStreamConstraint(target_pressure=pressure)

    return create_stream_constraint


@pytest.fixture
def chart_data(chart_data_factory) -> ChartData:
    return chart_data_factory.from_design_point(1000, 60_000, 0.7)


@pytest.mark.snapshot
@pytest.mark.inlinesnapshot
def test_speed_solver(fluid_service, stream_factory, process_system_factory, stream_constraint_factory, chart_data):
    chart_speeds = [curve.speed for curve in chart_data.get_adjusted_curves()]
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target_pressure = 90
    stream_constraint = stream_constraint_factory(pressure=target_pressure)
    process_system = process_system_factory(chart_data=chart_data, downstream_choke=Choke(fluid_service=fluid_service))

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
