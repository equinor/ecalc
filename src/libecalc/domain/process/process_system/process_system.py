from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PORT_ID = str


class ProcessSystem:
    def __init__(
        self,
        process_units: list[ProcessUnit],
        upstream_choke: Choke | None = None,
        downstream_choke: Choke | None = None,
    ):
        self._process_units = process_units
        self._upstream_choke = upstream_choke
        self._downstream_choke = downstream_choke

    def get_shaft(self) -> Shaft:
        return self._shaft

    def get_downstream_choke(self) -> Choke | None:
        return self._downstream_choke

    def get_upstream_choke(self) -> Choke | None:
        return self._upstream_choke

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        process_units: list[ProcessUnit] = []
        if self._upstream_choke is not None:
            process_units.append(self._upstream_choke)

        process_units.extend(self._process_units)

        if self._downstream_choke is not None:
            process_units.append(self._downstream_choke)

        current_inlet = inlet_stream
        for process_unit in process_units:
            current_inlet = process_unit.propagate_stream(inlet_stream=current_inlet)
        return current_inlet
