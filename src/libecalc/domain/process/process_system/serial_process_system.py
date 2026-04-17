from collections.abc import Sequence

from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.process_system.stream_propagator import StreamPropagator
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class SerialProcessSystem(ProcessSystem):
    def __init__(
        self,
        process_system_id: ProcessSystemId,
        propagators: Sequence[ProcessUnit | ProcessSystem],
    ):
        self._id = process_system_id
        self._propagators = propagators

    def get_id(self) -> ProcessSystemId:
        return self._id

    def get_process_units(self) -> Sequence[ProcessUnit | ProcessSystem]:
        process_units: list[ProcessUnit | ProcessSystem] = []
        for propagator in self._propagators:
            if isinstance(propagator, ProcessSystem):
                process_units.extend(propagator.get_process_units())
            else:
                process_units.append(propagator)
        return process_units

    def get_propagators(self) -> Sequence[StreamPropagator]:
        return self._propagators

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        current_inlet = inlet_stream
        for process_unit in self._propagators:
            current_inlet = process_unit.propagate_stream(inlet_stream=current_inlet)
        return current_inlet
