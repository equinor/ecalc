from libecalc.common.logger import logger
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class Splitter:
    """
    A class representing a splitter that divides a fluid stream into multiple output streams.

    Attributes:
        number_of_outputs (int): The number of output streams.
        _rates_out_of_splitter (list[float]): The flow rates for the first (number_of_outputs - 1) outputs.
    """

    def __init__(self, number_of_outputs: int, rates_out_of_splitter: list[float] | None = None):
        """
        Initializes the Splitter instance.

        Args:
            number_of_outputs (int): The number of output streams. Must be larger than 0.
            rates_out_of_splitter (list[float] | None): The flow rates for the first (number_of_outputs - 1) outputs.
                If None, initializes with zero flow rates.

        Raises:
            ValueError: If the length of rates_out_of_splitter does not match (number_of_outputs - 1).
        """
        self.number_of_outputs = number_of_outputs
        assert isinstance(self.number_of_outputs, int) and self.number_of_outputs > 0

        self._rates_out_of_splitter = (
            [0.0] * (number_of_outputs - 1) if rates_out_of_splitter is None else rates_out_of_splitter
        )
        assert len(self._rates_out_of_splitter) == self.number_of_outputs - 1

    @property
    def rates_out_of_splitter(self) -> list[float]:
        """
        Gets the flow rates for the first (number_of_outputs - 1) outputs.

        Returns:
            list[float]: The flow rates for the outputs.
        """
        return self._rates_out_of_splitter

    @rates_out_of_splitter.setter
    def rates_out_of_splitter(self, rates: list[float] | None):
        """
        Sets the flow rates for the first (number_of_outputs - 1) outputs.

        Args:
            rates (list[float] | None): The new flow rates. If None, initializes with zero flow rates.

        Raises:
            ValueError: If the length of rates does not match (number_of_outputs - 1).
        """
        self._rates_out_of_splitter = [0.0] * (self.number_of_outputs - 1) if rates is None else rates
        assert len(self._rates_out_of_splitter) == self.number_of_outputs - 1

    def split_stream(self, stream: FluidStream) -> list[FluidStream]:
        """
        Splits the input fluid stream into multiple output streams.

        The flow rates for the first (number_of_outputs - 1) outputs are taken from rates_out_of_splitter.
        The flow rate for the last output is calculated to ensure mass balance. If the sum of rates_out_of_splitter
        exceeds the input stream rate (checked against FLOATING_POINT_PRECISION), an exception is raised.

        Args:
            stream (FluidStream): The fluid stream to be split.

        Returns:
            list[FluidStream]: A list of FluidStream objects representing the output streams.

        Raises:
            IllegalStateException: If the sum of rates_out_of_splitter exceeds the input stream rate.
        """
        last_rate = stream.standard_rate - sum(self.rates_out_of_splitter)
        if last_rate < 0:
            logger.warning(
                f"Sum of output rates from splitter slightly exceeds input stream rate, probably due to floating point precision. "
                f"Input stream rate: {stream.standard_rate}, "
                f"Sum of output rates: {sum(self.rates_out_of_splitter)}. "
                f"Correcting last output rate to zero."
            )
            last_rate = 0.0
        all_rates_out_of_splitter = self.rates_out_of_splitter + [last_rate]
        split_fractions = [rate / sum(all_rates_out_of_splitter) for rate in all_rates_out_of_splitter]
        return [
            FluidStream(
                thermo_system=stream.thermo_system,
                mass_rate_kg_per_h=stream.mass_rate_kg_per_h * split_fraction,
            )
            for split_fraction in split_fractions
        ]
