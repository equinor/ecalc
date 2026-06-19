from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class Outlet(ProcessUnit):
    """
    A process unit that is the destination for the outlet streams, and where we test the
    outlet criteria on. Does not alter the process stream, and the stream does not go through it,
    but "ends" at it.

    We could e.g. say that it has a business criteria/policy, that a given outlet pressure MUST
    be expected here, otherwise it is considered a failure.

    This is like a sink in a streaming system - where it all ends
    """

    def __init__(self, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return inlet_stream  # TODO: Copy?
