import pytest

from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class SpeedProcessUnit(ProcessUnit):
    def __init__(self, shaft: Shaft, fluid_service: FluidService):
        self._shaft = shaft
        self._fluid_service = fluid_service

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
    process_system_factory,
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

    process_system = process_system_factory(process_units=[SpeedProcessUnit(shaft=shaft, fluid_service=fluid_service)])

    def speed_func(configuration: SpeedConfiguration):
        shaft.set_speed(configuration.speed)
        return process_system.propagate_stream(inlet_stream=inlet_stream)

    solution = speed_solver.solve(speed_func)

    assert solution.success == solution_found

    assert solution.configuration.speed == expected_speed
    outlet_stream = speed_func(solution.configuration)
    assert outlet_stream.pressure_bara == expected_pressure
