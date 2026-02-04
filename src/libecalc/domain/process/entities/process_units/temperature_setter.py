from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class TemperatureSetter(ProcessUnit):
    def __init__(self, required_temperature_kelvin: float, fluid_service: FluidService):
        self._required_temperature_kelvin = required_temperature_kelvin
        self._fluid_service = fluid_service

    @property
    def required_temperature_kelvin(self) -> float:
        return self._required_temperature_kelvin

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """This process unit currently acts as both a cooler and a heater. This is because eCalc currently attaches
        all information about stream temperature to the compressor stage. We dont really know the temperature of the
        stream until the temperature setter is reached (stream could have standard temperature).

        If the inlet stream is hotter than the required temperature, it cools it down to the required temperature.
        If the inlet stream is cooler than the required temperature, it heats it up to the required temperature.

        TODO: When the YAML file has a full definition of inlet streams and hence temperatures are all defined in the
          correct place, make this unit into a cooler, that only reduces temperature, and raise an error if the inlet
          stream is cooler than the required temperature.

        Args:
            inlet_stream: The fluid stream to set the temperature of.

        Returns:
            A new FluidStream at the required temperature.
        """
        if inlet_stream.temperature_kelvin != self.required_temperature_kelvin:
            new_fluid = self._fluid_service.create_fluid(
                inlet_stream.fluid_model,
                inlet_stream.pressure_bara,
                self.required_temperature_kelvin,
            )
            return inlet_stream.with_new_fluid(new_fluid)
        return inlet_stream
