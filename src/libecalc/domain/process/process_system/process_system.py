from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PORT_ID = str


class ProcessSystem:
    def __init__(
        self,
        process_units: list[ProcessUnit],
    ):
        self._process_units = process_units

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        current_inlet = inlet_stream
        for process_unit in self._process_units:
            current_inlet = process_unit.propagate_stream(inlet_stream=current_inlet)
        return current_inlet

    @property
    def contains_splitter(self):
        return any(isinstance(process_unit, Splitter) for process_unit in self._process_units)

    @property
    def contains_mixer(self):
        return any(isinstance(process_unit, Mixer) for process_unit in self._process_units)

    @property
    def has_multiple_streams(self):
        return self.contains_splitter or self.contains_mixer
