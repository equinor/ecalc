from libecalc.domain.process.entities.process_units.compressor_stage import CompressorStage
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream

InnerProcess = CompressorStage | ProcessSystem[CompressorStage]


class RecirculationLoop(ProcessUnit):
    def __init__(self, inner_process: InnerProcess, fluid_service: FluidService, inner_rate: float | None = None):
        self._inner_rate = inner_rate
        self._inner_process = inner_process
        self._fluid_service = fluid_service
        self._recirculation_rate = None

    def get_inner_process(self) -> InnerProcess:
        return self._inner_process

    def set_inner_rate(self, rate: float):
        self._inner_rate = rate

    def get_recirculation_rate(self) -> float:
        assert self._recirculation_rate is not None
        return self._recirculation_rate

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if self._inner_rate is None:
            self._recirculation_rate = 0
            # Do nothing
            return self._inner_process.propagate_stream(inlet_stream=inlet_stream)

        recirculation_rate = self._inner_rate - inlet_stream.standard_rate_sm3_per_day
        self._recirculation_rate = recirculation_rate

        inner_inlet_stream = self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day + recirculation_rate,
        )

        inner_outlet_stream = self._inner_process.propagate_stream(inlet_stream=inner_inlet_stream)

        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inner_outlet_stream.fluid_model,
            pressure_bara=inner_outlet_stream.pressure_bara,
            temperature_kelvin=inner_outlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inner_outlet_stream.standard_rate_sm3_per_day - recirculation_rate,
        )
