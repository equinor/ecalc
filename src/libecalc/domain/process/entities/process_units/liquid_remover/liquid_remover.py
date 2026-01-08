from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants


class LiquidRemover:
    def __init__(self, fluid_service: FluidService):
        self._fluid_service = fluid_service

    def remove_liquid(self, stream: FluidStream) -> FluidStream:
        """
        Removes liquid from the fluid stream.

        Args:
            stream: The fluid stream to be scrubbed.

        Returns:
            FluidStream: A new FluidStream with liquid removed.
        """
        if stream.vapor_fraction_molar < ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            new_fluid = self._fluid_service.remove_liquid(stream.fluid)
            return stream.with_new_fluid(new_fluid)
        else:
            return stream
