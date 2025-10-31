from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class RateModifier:
    """A unit that modifies the flow rate of a fluid stream. It is meant to be used in conjunction with compressors,
    to mimic an anti-surge recirculation loop.

    There is one rate modifier for increasing the flow rate before compression
    and one for decreasing the flow rate after compression.

    Attributes:
    """

    def __init__(self, recirculation_mass_rate: float = 0.0):
        self._recirculation_mass_rate = recirculation_mass_rate
        self._maximum_flow_rate = None

    @property
    def recirculation_mass_rate(self) -> float:
        return self._recirculation_mass_rate

    @recirculation_mass_rate.setter
    def recirculation_mass_rate(self, value: float):
        self._recirculation_mass_rate = value

    @property
    def maximum_flow_rate(self) -> float:
        return self._maximum_flow_rate

    @maximum_flow_rate.setter
    def maximum_flow_rate(self, value: float):
        self._maximum_flow_rate = value

    def add_rate(self, stream: FluidStream):
        """Increase the flow rate before compression."""
        return FluidStream(
            thermo_system=stream.thermo_system,
            mass_rate_kg_per_h=stream.mass_rate_kg_per_h + self.recirculation_mass_rate,
        )

    def remove_rate(self, stream: FluidStream):
        """Decrease the flow rate after compression."""
        return FluidStream(
            thermo_system=stream.thermo_system,
            mass_rate_kg_per_h=stream.mass_rate_kg_per_h - self.recirculation_mass_rate,
        )
