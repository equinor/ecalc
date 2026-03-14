from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.gas_compressor import GasCompressor
from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class RecirculationLoop(ProcessSystem):
    def __init__(
        self,
        process_system_id: ProcessSystemId,
        inner_process: ProcessSystem,
        fluid_service: FluidService,
        recirculation_rate: float = 0,
    ):
        self._id = process_system_id
        self._inner_process = inner_process
        self._fluid_service = fluid_service
        self._recirculation_rate = recirculation_rate
        self._validate_inner_process()

    def _validate_inner_process(self):
        assert isinstance(self._inner_process, ProcessSystem), "Recirculation loop should contain a ProcessSystem"
        for process_unit in self._inner_process.get_process_units():
            if isinstance(process_unit, Splitter | Mixer):
                raise DomainValidationException("Recirculation loop cannot contain splitters or mixers")

    def get_id(self) -> ProcessSystemId:
        return self._id

    def get_process_units(self):
        return self._inner_process.get_process_units()

    def set_recirculation_rate(self, rate: float):
        self._recirculation_rate = rate

    def get_recirculation_rate(self) -> float:
        assert self._recirculation_rate is not None
        return self._recirculation_rate

    def get_recirculation_range(self, inlet_stream: FluidStream) -> Boundary:
        """Delegate to the inner GasCompressor to determine the recirculation range.

        The inlet_stream is the stream entering the RecirculationLoop (i.e., the true
        process inlet, before recirculation is added). Works for individual-ASV loops
        that wrap a single GasCompressor.
        """
        compressors = [u for u in self.get_process_units() if isinstance(u, GasCompressor)]
        if len(compressors) != 1:
            raise ValueError(
                f"get_recirculation_range requires exactly one GasCompressor inside the loop, "
                f"found {len(compressors)}."
            )
        return compressors[0].get_recirculation_range(inlet_stream)

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
