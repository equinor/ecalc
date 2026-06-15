from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class Inlet(ProcessUnit):
    """
    Inlet, or Feed, is where a process stream is considered born/created in eCalc. We just know
    that the inlet stream conditions are given at this point.

    This is like a source in a streaming system - where it all starts.
    """

    def __init__(self, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return inlet_stream  # TODO: Copy?
