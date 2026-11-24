from collections.abc import Sequence

import pytest

from libecalc.common.units import UnitConstants
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.stream_distribution.liquid_common_stream_distribution import LiquidCommonStreamDistribution
from libecalc.process.pump.stream_distribution.liquid_individual_stream_distribution import (
    LiquidIndividualStreamDistribution,
)
from libecalc.process.pump.stream_distribution.liquid_priorities_stream_distribution import (
    HasLiquidValidity,
    LiquidPrioritiesStreamDistribution,
)
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3

MAXIMUM_RATE = 800.0


class StubItem(HasLiquidValidity):
    """Valid up to ``MAXIMUM_RATE``."""

    def is_valid(self, inlet_stream: LiquidStream) -> bool:
        return inlet_stream.volumetric_rate_m3_per_hour <= MAXIMUM_RATE


def _stream(rate_m3_per_hour: float, pressure_bara: float = 10.0) -> LiquidStream:
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * UnitConstants.HOURS_PER_DAY,
        pressure_bara=pressure_bara,
        density_kg_per_m3=DENSITY_KG_PER_M3,
    )


def _priorities(rates_m3_per_hour_by_distribution: Sequence[Sequence[float]]) -> LiquidPrioritiesStreamDistribution:
    return LiquidPrioritiesStreamDistribution(
        stream_distributions=[
            LiquidIndividualStreamDistribution([_stream(rate) for rate in rates])
            for rates in rates_m3_per_hour_by_distribution
        ],
        items=[StubItem(), StubItem()],
    )


@pytest.mark.parametrize(
    "rates_m3_per_hour_by_distribution, selected_index",
    [
        pytest.param([[600.0, 0.0], [300.0, 300.0]], 0, id="the first of two valid ones"),
        pytest.param([[1500.0, 0.0], [750.0, 750.0], [300.0, 300.0]], 1, id="the first valid one"),
        pytest.param([[1500.0, 0.0], [0.0, 1500.0], [1500.0, 1500.0]], 2, id="the last one when none is valid"),
    ],
)
def test_selects_the_first_stream_distribution_where_every_item_is_valid_else_the_last(
    rates_m3_per_hour_by_distribution, selected_index
):
    stream_distribution = _priorities(rates_m3_per_hour_by_distribution)

    index, streams = stream_distribution.select()

    assert index == selected_index
    assert [stream.volumetric_rate_m3_per_hour for stream in streams] == pytest.approx(
        rates_m3_per_hour_by_distribution[selected_index]
    )
    assert stream_distribution.get_streams() == streams


def test_common_stream_is_divided_by_the_rate_fractions():
    stream_distribution = LiquidCommonStreamDistribution(
        inlet_stream=_stream(1200.0, pressure_bara=7.0), rate_fractions=[0.25, 0.75, 0.0]
    )

    streams = stream_distribution.get_streams()

    assert [stream.volumetric_rate_m3_per_hour for stream in streams] == pytest.approx([300.0, 900.0, 0.0])
    assert [stream.pressure_bara for stream in streams] == [7.0, 7.0, 7.0]
    assert [stream.density_kg_per_m3 for stream in streams] == [DENSITY_KG_PER_M3] * 3


@pytest.mark.parametrize(
    "rates_m3_per_hour_by_distribution",
    [
        pytest.param([], id="no stream distribution"),
        pytest.param([[600.0, 0.0], [600.0]], id="another number of streams than items"),
    ],
)
def test_rejects_stream_distributions_that_do_not_match_the_items(rates_m3_per_hour_by_distribution):
    with pytest.raises(ValueError):
        _priorities(rates_m3_per_hour_by_distribution)
