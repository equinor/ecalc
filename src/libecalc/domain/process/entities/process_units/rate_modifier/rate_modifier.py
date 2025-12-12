from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class RateModifier:
    """
    A unit that modifies the flow rate of a fluid stream. It is meant to be used
    in conjunction with compressors, to mimic an anti-surge recirculation loop.

    There is one rate modifier (add_rate) for increasing the flow rate before compression
    and one (remove_rate) for decreasing the flow rate after compression.

    Attributes:
        _compressor_chart (CompressorChart): The compressor chart used to determine
            the maximum and minimum flow rates based on the compressor speed.
        _additional_mass_rate (float): The additional mass rate (in kg/h) added
            to the fluid stream.
        _mass_rate_to_recirculate (float): The fixed mass rate (in kg/h) to
            recirculate. If set, it clears any fraction-based setting.
        _fraction_of_available_capacity_to_recirculate (float): The fraction
            (0 to 1) of the compressor's available capacity to recirculate.
            If set, it clears any fixed mass rate setting.
    """

    def __init__(self, compressor_chart: ChartData):
        """
        Initialize the RateModifier with a compressor chart.

        Args:
            compressor_chart (CompressorChart): The compressor chart used to
                determine flow rate limits based on the compressor speed.
        """
        self._compressor_chart = CompressorChart(compressor_chart)
        self._additional_mass_rate = 0.0
        self._mass_rate_to_recirculate: float = None
        self._fraction_of_available_capacity_to_recirculate: float = None

    @property
    def mass_rate_to_recirculate(self) -> float:
        """
        Get the fixed mass rate to recirculate.

        Returns:
            float: The mass rate to recirculate in kg/h.
        """
        return self._mass_rate_to_recirculate

    @mass_rate_to_recirculate.setter
    def mass_rate_to_recirculate(self, value: float):
        """
        Set the fixed mass rate to recirculate in kg/h.

        Setting this value will clear any fraction-based recirculation setting.

        Args:
            value (float): The mass rate to recirculate in kg/h.
        """
        self._mass_rate_to_recirculate = value
        self._fraction_of_available_capacity_to_recirculate = None

    @property
    def fraction_of_available_capacity_to_recirculate(self) -> float:
        """
        Get the fraction of the compressor's available capacity to recirculate.

        Returns:
            float: The fraction of available capacity to recirculate (0 to 1).
        """
        return self._fraction_of_available_capacity_to_recirculate

    @fraction_of_available_capacity_to_recirculate.setter
    def fraction_of_available_capacity_to_recirculate(self, value: float):
        """
        Set the fraction of the compressor's available capacity to recirculate.

        Setting this value will clear any fixed mass rate recirculation setting.

        Args:
            value (float): The fraction of available capacity to recirculate (0 to 1).
        """
        self._fraction_of_available_capacity_to_recirculate = value
        self._mass_rate_to_recirculate = None

    def add_rate(self, stream: FluidStream, speed: float) -> FluidStream:
        """
        Increase the flow rate before compression.

        This method calculates the recirculation mass rate based on either a fixed
        mass rate or a fraction of the compressor's available capacity. It then
        adds the calculated additional mass rate to the input fluid stream and
        returns the modified stream.

        Args:
            stream (FluidStream): The input fluid stream whose flow rate is to be
                increased. It contains properties such as volumetric rate, density,
                and mass rate.
            speed (float): The speed of the compressor, which is used to determine
                the maximum and minimum flow rates from the compressor chart.

        Returns:
            FluidStream: A new fluid stream object with the updated mass flow rate.
        """
        # Get the current volumetric rate of the input stream
        actual_rate = stream.volumetric_rate

        # Retrieve the maximum and minimum flow rates for the compressor at the given speed
        max_rate = self._compressor_chart.maximum_rate_as_function_of_speed(speed)
        min_rate = self._compressor_chart.minimum_rate_as_function_of_speed(speed)

        # If the actual rate is below the minimum rate, recirculate enough to reach the minimum rate
        rate_needed_to_reach_minimum_flow = max(0, min_rate - actual_rate)

        # Calculate the available capacity of the compressor
        available_capacity = max(0, max_rate - (actual_rate + rate_needed_to_reach_minimum_flow))

        # Determine the additional rate to be added based on the available capacity
        # and the configured recirculation settings (either fraction-based or mass rate-based)
        if self._fraction_of_available_capacity_to_recirculate is not None:
            additional_rate = (
                rate_needed_to_reach_minimum_flow
                + self._fraction_of_available_capacity_to_recirculate * available_capacity
            )
        elif self._mass_rate_to_recirculate is not None:
            additional_rate = rate_needed_to_reach_minimum_flow + self._mass_rate_to_recirculate / stream.density
        else:
            additional_rate = rate_needed_to_reach_minimum_flow

        # Convert the additional rate to mass rate and store it
        self._additional_mass_rate = additional_rate * stream.density

        # Return a new FluidStream object with the updated mass flow rate
        return FluidStream(
            thermo_system=stream.thermo_system,
            mass_rate_kg_per_h=stream.mass_rate_kg_per_h + self._additional_mass_rate,
        )

    def remove_rate(self, stream: FluidStream):
        """
        Decrease the flow rate after compression.

        This method reduces the mass flow rate of the given fluid stream by
        subtracting the additional mass rate previously calculated and stored
        in the `_additional_mass_rate` attribute.

        Args:
            stream (FluidStream): The input fluid stream whose flow rate is to be
                decreased. It contains properties such as the thermodynamic system
                and mass flow rate.

        Returns:
            FluidStream: A new fluid stream object with the updated (reduced) mass
            flow rate.
        """
        return FluidStream(
            thermo_system=stream.thermo_system,
            mass_rate_kg_per_h=stream.mass_rate_kg_per_h - self._additional_mass_rate,
        )

    def reset_recirculation_settings(self):
        """
        Reset the recirculation settings.

        This method clears both the fixed mass rate and fraction-based recirculation
        settings, effectively resetting the RateModifier to its default state.
        """
        self._mass_rate_to_recirculate = None
        self._fraction_of_available_capacity_to_recirculate = None
