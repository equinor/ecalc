import pytest

from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_system.process_error import ProcessError, RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class RateCompressor(ProcessUnit):
    def __init__(self, fluid_service: FluidService, minimum_rate: float, maximum_rate: float):
        self._fluid_service = fluid_service
        self._minimum_rate = minimum_rate
        self._maximum_rate = maximum_rate

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if inlet_stream.volumetric_rate_m3_per_hour < self._minimum_rate:
            raise RateTooLowError()
        if inlet_stream.volumetric_rate_m3_per_hour > self._maximum_rate:
            raise RateTooHighError()
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + inlet_stream.standard_rate_sm3_per_day,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def rate_compressor_factory(fluid_service):
    def create_rate_compressor(minimum_rate: float, maximum_rate: float):
        return RateCompressor(
            fluid_service=fluid_service,
            minimum_rate=minimum_rate,
            maximum_rate=maximum_rate,
        )

    return create_rate_compressor


@pytest.mark.parametrize(
    "minimum_volumetric_rate, expected_recirculation_rate",
    [
        (30, 5039.0625),  # Recirc
        (10, 0),  # no recirc
    ],
)
def test_single(
    search_strategy_factory,
    root_finding_strategy,
    rate_compressor_factory,
    process_system_factory,
    fluid_service,
    stream_factory,
    minimum_volumetric_rate,
    expected_recirculation_rate,
):
    recirculation_loop = RecirculationLoop(
        inner_process=rate_compressor_factory(minimum_rate=minimum_volumetric_rate, maximum_rate=500),
        fluid_service=fluid_service,
    )
    process_system = process_system_factory(
        process_units=[recirculation_loop],
    )

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=10000,
        pressure_bara=20,
    )

    assert inlet_stream.volumetric_rate_m3_per_hour == 19.96851794096588

    if expected_recirculation_rate != 0:
        with pytest.raises(ProcessError):
            process_system.propagate_stream(inlet_stream=inlet_stream)

    recirculation_solver = RecirculationSolver(
        search_strategy=search_strategy_factory(tolerance=10e-3),
        root_finding_strategy=root_finding_strategy,
        recirculation_rate_boundary=Boundary(min=0, max=20000),
    )

    def recirculation_func(configuration: RecirculationConfiguration):
        recirculation_loop.set_recirculation_rate(configuration.recirculation_rate)
        return process_system.propagate_stream(inlet_stream)

    recirculation_solution = recirculation_solver.solve(recirculation_func)

    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)

    # TODO: Verify inlet_standard_rate + recirc_rate = compressor_rate
    assert recirculation_solution.success
    assert inlet_stream.standard_rate_sm3_per_day == pytest.approx(outlet_stream.standard_rate_sm3_per_day)
    assert recirculation_solution.configuration.recirculation_rate == expected_recirculation_rate
