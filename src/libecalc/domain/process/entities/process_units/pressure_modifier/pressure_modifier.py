from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class DifferentialPressureModifier:
    def __init__(self, differential_pressure: float, fluid_service: FluidService):
        self._differential_pressure = differential_pressure
        self._fluid_service = fluid_service

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
            stream: The incoming fluid stream.

        Returns:
            FluidStream: The processed fluid stream with adjusted pressure.
        """
        if self.differential_pressure == 0:
            return stream
        else:
            outlet_pressure = stream.pressure_bara - self.differential_pressure
            new_fluid = self._fluid_service.create_fluid(stream.fluid_model, outlet_pressure, stream.temperature_kelvin)
            return stream.with_new_fluid(new_fluid)
