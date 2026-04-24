from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants


class LiquidRemover(ProcessUnit):
    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId = ProcessUnit._create_id()):
        self._id = process_unit_id
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
