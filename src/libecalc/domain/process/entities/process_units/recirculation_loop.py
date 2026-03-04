from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream

InnerProcess = ProcessSystem | ProcessUnit


class RecirculationLoop(ProcessUnit):
    def __init__(
        self,
        inner_process: InnerProcess,
        fluid_service: FluidService,
        recirculation_rate: float = 0,
    ):
        self._inner_process = inner_process
        self._fluid_service = fluid_service
        self._recirculation_rate = recirculation_rate
        self._validate_inner_process()

    def _validate_inner_process(self):
        if isinstance(self._inner_process, Splitter):
            raise ValueError("Inner process cannot be a splitter")
        if isinstance(self._inner_process, Mixer):
            raise ValueError("Inner process cannot be a mixer")
        if isinstance(self._inner_process, ProcessSystem) and self._inner_process.has_multiple_streams:
            raise ValueError("Inner process cannot have multiple streams")

    def get_inner_process(self) -> InnerProcess:
        return self._inner_process

    def set_recirculation_rate(self, rate: float):
        self._recirculation_rate = rate

    def get_recirculation_rate(self) -> float:
        assert self._recirculation_rate is not None
        return self._recirculation_rate

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        inner_inlet_stream = self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day + self._recirculation_rate,
        )

        inner_outlet_stream = self._inner_process.propagate_stream(inlet_stream=inner_inlet_stream)

        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inner_outlet_stream.fluid_model,
            pressure_bara=inner_outlet_stream.pressure_bara,
            temperature_kelvin=inner_outlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inner_outlet_stream.standard_rate_sm3_per_day - self._recirculation_rate,
        )
