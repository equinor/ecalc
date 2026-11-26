from collections.abc import Sequence

from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.stream_distribution.liquid_stream_distribution import LiquidStreamDistribution


class LiquidCommonStreamDistribution(LiquidStreamDistribution):
    """One inlet stream divided between the pumps by rate fractions."""

    def __init__(self, inlet_stream: LiquidStream, rate_fractions: Sequence[float]):
        self._inlet_stream = inlet_stream
        self._rate_fractions = tuple(rate_fractions)

    def get_number_of_streams(self) -> int:
        return len(self._rate_fractions)

    def get_streams(self) -> list[LiquidStream]:
        return [
            self._inlet_stream.with_mass_rate(self._inlet_stream.mass_rate_kg_per_h * rate_fraction)
            for rate_fraction in self._rate_fractions
        ]
