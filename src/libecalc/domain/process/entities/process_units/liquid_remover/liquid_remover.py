from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import FluidServiceInterface, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants


@dataclass(frozen=True)
class LiquidRemover:
    @staticmethod
    def remove_liquid(stream: FluidStream, fluid_service: FluidServiceInterface) -> FluidStream:
        """
        Removes liquid from the fluid stream.

        Args:
            stream: The fluid stream to be scrubbed.
            fluid_service: Service for performing flash operations

        Returns:
            FluidStream: A new FluidStream with liquid removed.
        """
        if stream.vapor_fraction_molar < ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            new_fluid = fluid_service.remove_liquid(stream.fluid)
            return stream.with_new_fluid(new_fluid)
        else:
            return stream
