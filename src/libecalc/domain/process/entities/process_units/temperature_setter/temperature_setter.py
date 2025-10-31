from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


class TemperatureSetter:
    def __init__(self, required_temperature_kelvin: float):
        self._required_temperature_kelvin = required_temperature_kelvin

    @property
    def required_temperature_kelvin(self) -> float:
        return self._required_temperature_kelvin

    def set_temperature(self, stream: FluidStream) -> FluidStream:
        if stream.temperature_kelvin > self.required_temperature_kelvin:
            return stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stream.pressure_bara,
                    temperature_kelvin=self.required_temperature_kelvin,
                )
            )
        return stream
