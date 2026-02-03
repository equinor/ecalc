import pytest

from libecalc.domain.process.entities.process_units.compressor_stage import CompressorStage
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_system.process_error import OutsideCapacityError, ProcessError
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class RateCompressor(CompressorStage):
    def __init__(self, fluid_service: FluidService, minimum_rate: float):
        self._fluid_service = fluid_service
        self._minimum_rate = minimum_rate

    def get_minimum_rate(self) -> float:
        return self._minimum_rate

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if inlet_stream.standard_rate_sm3_per_day < self._minimum_rate:
            raise OutsideCapacityError("")
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + inlet_stream.standard_rate_sm3_per_day,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def rate_compressor_factory(fluid_service):
    def create_rate_compressor(minimum_rate: float):
        return RateCompressor(
            fluid_service=fluid_service,
            minimum_rate=minimum_rate,
        )

    return create_rate_compressor


def test_recirculation_solver(
    rate_compressor_factory,
    process_system_factory,
    fluid_service,
    stream_factory,
):
    recirculation_loop = RecirculationLoop(
        inner_process=rate_compressor_factory(minimum_rate=200), fluid_service=fluid_service, inner_rate=None
    )
    process_system = process_system_factory(
        process_units=[recirculation_loop],
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=100, pressure_bara=70)

    with pytest.raises(ProcessError):
        process_system.propagate_stream(inlet_stream=inlet_stream)

    recirculation_solver = RecirculationSolver(recirculation_loop=recirculation_loop)
    recirculation_solver.solve(process_system, inlet_stream)

    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)

    assert outlet_stream.pressure_bara == 270
    assert recirculation_loop.get_recirculation_rate() == 100
