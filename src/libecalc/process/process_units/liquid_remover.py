from typing import Final

from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class LiquidRemover(ProcessUnit):
    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """
        Removes liquid from the fluid stream.

        Args:
            inlet_stream: The fluid stream to be scrubbed.

        Returns:
            FluidStream: A new FluidStream with liquid removed.
        """
        if inlet_stream.vapor_fraction_molar < ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            new_fluid = self._fluid_service.remove_liquid(inlet_stream.fluid)
            return inlet_stream.with_new_fluid(new_fluid)
        else:
            return inlet_stream
