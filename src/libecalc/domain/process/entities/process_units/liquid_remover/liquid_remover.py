from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import FluidServiceInterface, FluidStream


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
        if stream.vapor_fraction_molar < 1.0:
            new_fluid = fluid_service.create_fluid(
                stream.fluid_model,
                stream.pressure_bara,
                stream.temperature_kelvin,
                remove_liquid=True,
            )
            return stream.with_new_fluid(new_fluid)
        else:
            return stream
