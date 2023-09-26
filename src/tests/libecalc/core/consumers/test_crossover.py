from datetime import datetime
from typing import List

import numpy as np
import pytest
from libecalc.common.stream import Stream
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.core.consumers.consumer_system import ConsumerSystem


def create_stream_from_rate(rate: List[float]) -> Stream:
    timesteps = [datetime(2020, 1, i + 1) for i in range(len(rate))]
    return Stream(
        rate=TimeSeriesRate(
            timesteps=timesteps,
            values=rate,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ),
        pressure=TimeSeriesFloat(
            timesteps=timesteps,
            values=[50] * len(rate),
            unit=Unit.BARA,
        ),
    )


class TestCrossover:
    parameterized_crossover_streams = [
        (
            [4, 4],
            [create_stream_from_rate([2, 2]), create_stream_from_rate([2, 2])],
            create_stream_from_rate([0, 0]),
            [create_stream_from_rate([2, 2]), create_stream_from_rate([2, 2])],
        ),  # All rates within capacity
        (
            [4, 4],
            [create_stream_from_rate([3, 3]), create_stream_from_rate([1, 1])],
            create_stream_from_rate([0, 0]),
            [create_stream_from_rate([3, 3]), create_stream_from_rate([1, 1])],
        ),  # All rates within capacity
        (  # Exceeds capacity, cross over required
            [4, 4],  # 4 for both timesteps
            [create_stream_from_rate([4, 4]), create_stream_from_rate([1, 1])],  # 4 in rate + 1 crossover, 1 exceeding
            create_stream_from_rate([1, 1]),  # 1 exceeding
            [
                create_stream_from_rate([4, 4]),
                create_stream_from_rate([0, 0]),
            ],  # we have capacity for first stream, but not 2nd stream
        ),
        (  # Exceeds capacity, cross over required
            [4, 4],  # 4 for both timesteps
            [create_stream_from_rate([5, 5])],  # 4 in rate
            create_stream_from_rate([1, 1]),  # 1 exceeding
            [create_stream_from_rate([4, 4])],
        ),
        (  # Exceeds capacity two times, cross over required
            [4, 4],  # 4 for both timesteps
            [create_stream_from_rate([5, 5]), create_stream_from_rate([2, 2])],  # 4 in rate
            create_stream_from_rate([3, 3]),  # 1 exceeding
            [create_stream_from_rate([4, 4]), create_stream_from_rate([0, 0])],
        ),
        (  # Exceeds capacity two times, cross over required
            [4, 4],  # 4 for both timesteps
            [create_stream_from_rate([5, 5]), create_stream_from_rate([0, 0])],  # 4 in rate
            create_stream_from_rate([1, 1]),  # 1 exceeding
            [create_stream_from_rate([4, 4]), create_stream_from_rate([0, 0])],
        ),
        (  # Exceeds capacity three times, cross over required
            [2, 2],  # 4 for both timesteps
            [create_stream_from_rate([3, 3]), create_stream_from_rate([1, 1]), create_stream_from_rate([1, 1])],
            create_stream_from_rate([3, 3]),  # 1 exceeding
            [create_stream_from_rate([2, 2]), create_stream_from_rate([0, 0]), create_stream_from_rate([0, 0])],
        ),
        (  # Under capacity
            [4, 4],  # 4 for both timesteps
            [create_stream_from_rate([2, 2]), create_stream_from_rate([1, 1])],  # 3 in rate, below 4
            create_stream_from_rate([0, 0]),
            [create_stream_from_rate([2, 2]), create_stream_from_rate([1, 1])],
        ),
    ]

    @pytest.mark.parametrize(
        "max_rate, streams, expected_crossover_stream, expected_streams_within_capacity",
        parameterized_crossover_streams,
    )
    def test_get_crossover_rates(
        self,
        max_rate,
        streams,
        expected_crossover_stream,
        expected_streams_within_capacity,
    ):
        """
        Test different realistic setups for crossover.
        Skipping test of edge-case where there are no streams, as that should be handled before this method.
        """
        crossover_stream, streams_within_capacity = ConsumerSystem._get_crossover_streams(max_rate, streams)
        assert np.array_equal(crossover_stream, expected_crossover_stream)
        assert np.array_equal(streams_within_capacity, expected_streams_within_capacity)
