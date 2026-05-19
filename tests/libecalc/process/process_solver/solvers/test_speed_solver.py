from typing import Final

import pytest

from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.process_solver.solver import RateTooHighFailure, RateTooLowFailure
from libecalc.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.process.shaft import Shaft, VariableSpeedShaft


class SpeedProcessUnit(ProcessUnit):
    def __init__(
        self,
        shaft: Shaft,
        fluid_service: FluidService,
        process_unit_id: ProcessUnitId | None = None,
    ):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._shaft = shaft
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        speed = self._shaft.get_speed()
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.mark.parametrize(
    "target_pressure, speed_boundary, inlet_pressure, expected_speed, expected_pressure, solution_found",
    [
        (300, Boundary(min=200, max=600), 100, 200, 300, True),  # Solution found
        (1000, Boundary(min=200, max=600), 100, 600, 700, False),  # Solution not found, max speed
        (50, Boundary(min=200, max=600), 25, 200, 225, False),  # Solution not found, min speed
    ],
)
def test_speed_solver(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    shaft,
    fluid_service,
    target_pressure,
    speed_boundary,
    inlet_pressure,
    expected_speed,
    expected_pressure,
    solution_found,
):
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=speed_boundary,
        target_pressure=target_pressure,
    )
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=1000,
        pressure_bara=inlet_pressure,
    )

    process_units = [SpeedProcessUnit(shaft=shaft, fluid_service=fluid_service)]

    def speed_func(configuration: SpeedConfiguration):
        shaft.set_speed(configuration.speed)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    solution = speed_solver.solve(speed_func)

    assert solution.success == solution_found

    assert solution.configuration.speed == expected_speed
    outlet_stream = speed_func(solution.configuration)
    assert outlet_stream.pressure_bara == expected_pressure


def test_max_speed_rate_too_high_returns_capacity_failure(
    search_strategy_factory,
    root_finding_strategy,
):
    process_unit_id = ProcessUnit._create_id()
    actual_rate = 2000.0
    boundary_rate = 1000.0
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )

    def speed_func(configuration: SpeedConfiguration):
        raise RateTooHighError(
            process_unit_id=process_unit_id,
            actual_rate=actual_rate,
            boundary_rate=boundary_rate,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert solution.configuration.speed == 600
    assert isinstance(solution.failure, RateTooHighFailure)
    assert solution.failure.actual_rate_m3_per_hour == actual_rate
    assert solution.failure.maximum_rate_m3_per_hour == boundary_rate
    assert solution.failure.source_id == process_unit_id


def test_max_speed_rate_too_low_returns_capacity_failure(
    search_strategy_factory,
    root_finding_strategy,
):
    process_unit_id = ProcessUnit._create_id()
    actual_rate = 50.0
    boundary_rate = 100.0
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )

    def speed_func(configuration: SpeedConfiguration):
        raise RateTooLowError(
            process_unit_id=process_unit_id,
            actual_rate=actual_rate,
            boundary_rate=boundary_rate,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert solution.configuration.speed == 600
    assert isinstance(solution.failure, RateTooLowFailure)
    assert solution.failure.actual_rate_m3_per_hour == actual_rate
    assert solution.failure.minimum_rate_m3_per_hour == boundary_rate
    assert solution.failure.source_id == process_unit_id
