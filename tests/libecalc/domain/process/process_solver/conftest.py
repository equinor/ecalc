import pytest

from libecalc.domain.process.entities.process_units.gas_compressor import GasCompressor
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_unit import ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class SpeedGasCompressor(GasCompressor):
    """
    Test double that makes speed->pressure mapping deterministic:

      outlet_pressure = inlet_pressure + shaft_speed

    Extends GasCompressor directly so it is recognised by isinstance checks.
    The capacity-related methods return wide limits to avoid interfering with
    tests that focus on solver orchestration.
    """

    def __init__(self, shaft: VariableSpeedShaft, fluid_service: FluidService):
        # Do NOT call super().__init__() — no CompressorChart is needed.
        self._id = create_process_unit_id()
        self._shaft = shaft
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def get_speed_boundary(self) -> Boundary:
        return Boundary(min=200.0, max=600.0)

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        return 1e30

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        return 0.0

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        speed = self._shaft.get_speed()
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def speed_compressor_factory(fluid_service):
    def create(shaft: VariableSpeedShaft):
        return SpeedGasCompressor(shaft=shaft, fluid_service=fluid_service)

    return create
