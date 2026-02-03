import pytest

from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedSolver
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
    "target_pressure, speed_boundary, inlet_pressure, expected_speed, expected_pressure",
    [
        (300, Boundary(min=200, max=600), 100, 200, 300),  # Solution found
        (1000, Boundary(min=200, max=600), 100, 600, 700),  # Solution not found, max speed
        (50, Boundary(min=200, max=600), 25, 200, 225),  # Solution not found, min speed
    ],
)
def test_speed_solver(
    stream_factory,
    process_system_factory,
    shaft,
    fluid_service,
    target_pressure,
    speed_boundary,
    inlet_pressure,
    expected_speed,
    expected_pressure,
):
    speed_solver = SpeedSolver(
        boundary=speed_boundary,
        target_pressure=target_pressure,
    )
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=1000,
        pressure_bara=inlet_pressure,
    )

    process_system = process_system_factory(
        shaft=shaft, process_units=[SpeedProcessUnit(shaft=shaft, fluid_service=fluid_service)]
    )

    outlet_stream = speed_solver.solve(process_system=process_system, inlet_stream=inlet_stream)

    assert shaft.get_speed() == expected_speed
    assert outlet_stream.pressure_bara == expected_pressure
