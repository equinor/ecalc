from libecalc.domain.process.entities.shaft import Shaft
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
        _shaft (Shaft): The shaft associated with the compressor.
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

    def __init__(self, compressor_chart: ChartData, shaft: Shaft):
        """
        Initialize the RateModifier with a compressor chart.

        Args:
            compressor_chart (CompressorChart): The compressor chart used to
                determine flow rate limits based on the compressor speed.
            shaft (Shaft): The shaft associated with the compressor.

        """
        self._shaft = shaft
        self._compressor_chart = CompressorChart(compressor_chart)
        self._additional_mass_rate = 0.0
        self._mass_rate_to_recirculate: float = None  # from COMMON ASV
        self._fraction_of_available_capacity_to_recirculate: float = None

    @property
    def shaft(self) -> Shaft | None:
        return self._shaft

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    @property
    def speed(self) -> float | None:
        if self.shaft is not None:
            return self.shaft.get_speed()
        return None

    def get_max_rate(self) -> float:
        assert self.speed is not None, "Speed must be set before getting max rate."
        return self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)

    def get_min_rate(self) -> float:
        assert self.speed is not None, "Speed must be set before getting min rate."
        return self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)

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

    @property
    def add_rate_based_on_fraction_of_available_capacity(self) -> bool:
        """
        Check if recirculation is based on a fraction of available capacity.

        Returns:
            bool: True if recirculation is based on fraction, False otherwise.
        """
        return self._fraction_of_available_capacity_to_recirculate is not None

    @property
    def add_rate_based_on_given_mass_rate(self) -> bool:
        """
        Check if recirculation is based on a fixed mass rate.

        Returns:
            bool: True if recirculation is based on fixed mass rate, False otherwise.
        """
        return self._mass_rate_to_recirculate is not None

    def add_rate(self, stream: FluidStream) -> FluidStream:
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
        actual_rate = stream.volumetric_rate_m3_per_hour
        additional_rate = 0.0

        # Add fixed mass rate recirculation if specified (COMMON ASV pressure control)
        if self.add_rate_based_on_given_mass_rate:
            additional_rate += self._mass_rate_to_recirculate / stream.density
            actual_rate += additional_rate

        # Check if rate has already reached minimum flow rate at given speed
        max_rate = self.get_max_rate()
        min_rate = self.get_min_rate()

        # Add fraction-based recirculation if specified (ASV individual rate pressure control)
        if self.add_rate_based_on_fraction_of_available_capacity:
            available_capacity = max(0, max_rate - actual_rate)
            additional_rate += self._fraction_of_available_capacity_to_recirculate * available_capacity
            actual_rate += additional_rate

        rate_needed_to_reach_minimum_flow = max(0, min_rate - actual_rate)

        # If necessary add rate to reach minimum flow rate
        if rate_needed_to_reach_minimum_flow > 0:
            additional_rate += rate_needed_to_reach_minimum_flow
            actual_rate += rate_needed_to_reach_minimum_flow

        self._additional_mass_rate = additional_rate * stream.density

        # Return a new FluidStream object with the updated mass flow rate
        return stream.with_mass_rate(stream.mass_rate_kg_per_h + self._additional_mass_rate)

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
        return stream.with_mass_rate(stream.mass_rate_kg_per_h - self._additional_mass_rate)

    def reset(self):
        """
        Reset the recirculation settings.

        This method clears both the fixed mass rate and fraction-based recirculation
        settings, effectively resetting the RateModifier to its default state.
        """
        self._mass_rate_to_recirculate = None
        self._fraction_of_available_capacity_to_recirculate = None
