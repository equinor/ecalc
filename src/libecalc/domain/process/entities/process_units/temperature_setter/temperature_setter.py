from libecalc.domain.process.value_objects.fluid_stream import FluidServiceInterface, FluidStream


class TemperatureSetter:
    def __init__(self, required_temperature_kelvin: float):
        self._required_temperature_kelvin = required_temperature_kelvin

    @property
    def required_temperature_kelvin(self) -> float:
        return self._required_temperature_kelvin

    def set_temperature(self, stream: FluidStream, fluid_service: FluidServiceInterface) -> FluidStream:
        """Cool the inlet stream to the required temperature.

        Args:
            stream: The fluid stream to cool
            fluid_service: Service for performing flash operations

        Returns:
            A new FluidStream at the required temperature (or the original if already cool enough)
        """
        if stream.temperature_kelvin > self.required_temperature_kelvin:
            new_fluid = fluid_service.create_fluid(
                stream.fluid_model,
                stream.pressure_bara,
                self.required_temperature_kelvin,
            )
            return stream.with_new_fluid(new_fluid)
        return stream
