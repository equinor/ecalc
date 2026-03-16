from collections.abc import Sequence

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter import Splitter
from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class DirectMixer(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, mix_rate: float, fluid_service: FluidService):
        self._id = process_unit_id
        self._fluid_service = fluid_service
        self._mix_rate = mix_rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day + self._mix_rate,
        )

    def get_mix_rate(self) -> float:
        return self._mix_rate

    def set_mix_rate(self, mix_rate: float):
        self._mix_rate = mix_rate


class DirectSplitter(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, split_rate: float, fluid_service: FluidService):
        self._id = process_unit_id
        self._fluid_service = fluid_service
        self._split_rate = split_rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day - self._split_rate,
        )

    def set_split_rate(self, split_rate: float):
        self._split_rate = split_rate


class RecirculationLoop(ProcessSystem):
    def __init__(
        self,
        process_system_id: ProcessSystemId,
        inner_process: ProcessSystem | ProcessUnit,
        fluid_service: FluidService,
        recirculation_rate: float = 0,
    ):
        self._id = process_system_id
        self._inner_process = inner_process
        self._fluid_service = fluid_service
        self._validate_inner_process()
        self._mixer = DirectMixer(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
            mix_rate=recirculation_rate,
        )
        self._splitter = DirectSplitter(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
            split_rate=recirculation_rate,
        )

    def get_mechanical_components(self) -> list:
        return []

    def _validate_inner_process(self):
        if not isinstance(self._inner_process, ProcessSystem | ProcessUnit):
            raise DomainValidationException(
                "Recirculation loop should contain a ProcessSystem with a compressor or a single compressor"
            )
        if isinstance(self._inner_process, ProcessSystem):
            for process_unit in self._inner_process.get_process_units():
                if isinstance(process_unit, Splitter | Mixer):
                    raise DomainValidationException("Recirculation loop cannot contain splitters or mixers")
        if isinstance(self._inner_process, ProcessUnit):
            if not isinstance(self._inner_process, Compressor):
                raise DomainValidationException(
                    "Recirculation loop should contain a ProcessSystem with a compressor or a single compressor"
                )

    def get_id(self) -> ProcessSystemId:
        return self._id

    def get_process_units(self) -> Sequence[ProcessUnit | ProcessSystem]:
        if isinstance(self._inner_process, ProcessSystem):
            return [
                self._mixer,
                *self._inner_process.get_process_units(),
                self._splitter,
            ]
        else:
            return [
                self._mixer,
                self._inner_process,
                self._splitter,
            ]

    def set_recirculation_rate(self, rate: float):
        self._mixer.set_mix_rate(rate)
        self._splitter.set_split_rate(rate)

    def get_recirculation_rate(self) -> float:
        return self._mixer.get_mix_rate()

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        inner_inlet_stream = self._mixer.propagate_stream(inlet_stream=inlet_stream)

        inner_outlet_stream = self._inner_process.propagate_stream(inlet_stream=inner_inlet_stream)

        return self._splitter.propagate_stream(inlet_stream=inner_outlet_stream)
