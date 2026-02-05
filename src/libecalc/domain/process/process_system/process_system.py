from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PORT_ID = str


class ProcessSystem:
    def __init__(
        self,
        process_units: list[ProcessUnit],
    ):
        self._process_units = process_units

    def get_shaft(self) -> Shaft:
        return self._shaft

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        current_inlet = inlet_stream
        for process_unit in self._process_units:
            current_inlet = process_unit.propagate_stream(inlet_stream=current_inlet)
        return current_inlet
