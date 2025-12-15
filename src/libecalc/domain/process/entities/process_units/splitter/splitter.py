from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class Splitter:
    def __init__(self, number_of_outputs: int):
        self.number_of_outputs = number_of_outputs

    def split_stream(self, stream: FluidStream, split_fractions: list[float]) -> list[FluidStream]:
        """
        Splits the fluid stream into streams based on the split fractions.

        Args:
            stream (FluidStream): The fluid stream to be split.
            split_fractions (Sequence[float]): The fractions of the stream to go to the different output streams (0.0 to 1.0).

        Returns:
            list[FluidStream]: A list containing the resulting FluidStreams.
        """
        # make sure number of split fractions matches number of outputs
        if len(split_fractions) != self.number_of_outputs:
            raise ValueError("Number of split fractions must match number of outputs.")

        # normalize split fractions
        total = sum(split_fractions)
        normalized_fractions = [f / total for f in split_fractions]

        return [
            FluidStream(
                thermo_system=stream.thermo_system,
                mass_rate_kg_per_h=stream.mass_rate_kg_per_h * split_fraction,
            )
            for split_fraction in normalized_fractions
        ]
