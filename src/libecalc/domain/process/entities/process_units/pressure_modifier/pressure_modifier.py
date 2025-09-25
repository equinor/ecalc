from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


class DifferentialPressureModifier:
    def __init__(self, differential_pressure: float = 0):
        self._differential_pressure = differential_pressure

    @property
    def differential_pressure(self) -> float:
        return self._differential_pressure

    @differential_pressure.setter
    def differential_pressure(self, value: float):
        self._differential_pressure = value

    def modify_pressure(self, stream: FluidStream) -> FluidStream:
        """
        Adjusts the stream pressure to achieve the set differential pressure.

        Args:
            stream (FluidStream): The incoming fluid stream.

        Returns:
            FluidStream: The processed fluid stream with adjusted pressure.
        """
        if self.differential_pressure == 0:
            return stream
        else:
            outlet_pressure = stream.pressure_bara - self.differential_pressure
            return stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=outlet_pressure,
                    temperature_kelvin=stream.temperature_kelvin,
                ),
            )
