from datetime import datetime

import pytest
from libecalc.common.units import Unit
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.domain.stream_conditions import Pressure, Rate, StreamConditions


def create_stream_from_rate(rate: float, name: str = "inlet") -> StreamConditions:
    return StreamConditions(
        id="name",
        name=name,
        timestep=datetime(2019, 1, 1),
        rate=Rate(
            value=rate,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ),
        pressure=Pressure(
            value=50,
            unit=Unit.BARA,
        ),
    )


class TestCrossover:
    parameterized_crossover_streams = [
        (
            4,
            [create_stream_from_rate(2), create_stream_from_rate(2)],
            create_stream_from_rate(0, name="test-stream-please-ignore"),
            [create_stream_from_rate(2), create_stream_from_rate(2)],
        ),  # All rates within capacity
        (
            4,
            [create_stream_from_rate(3), create_stream_from_rate(1)],
            create_stream_from_rate(0, name="test-stream-please-ignore"),
            [create_stream_from_rate(3), create_stream_from_rate(1)],
        ),  # All rates within capacity
        (  # Exceeds capacity, cross over required
            4,
            [create_stream_from_rate(4), create_stream_from_rate(1)],  # 4 in rate + 1 crossover, 1 exceeding
            create_stream_from_rate(1, name="test-stream-please-ignore"),  # 1 exceeding
            [
                create_stream_from_rate(4),
                create_stream_from_rate(0),
            ],  # we have capacity for first stream, but not 2nd stream
        ),
        (  # Exceeds capacity, cross over required
            4,
            [create_stream_from_rate(5)],  # 4 in rate
            create_stream_from_rate(1, name="test-stream-please-ignore"),  # 1 exceeding
            [create_stream_from_rate(4)],
        ),
        (  # Exceeds capacity two times, cross over required
            4,
            [create_stream_from_rate(5), create_stream_from_rate(2)],  # 4 in rate
            create_stream_from_rate(3, name="test-stream-please-ignore"),  # 1 exceeding
            [create_stream_from_rate(4), create_stream_from_rate(0)],
        ),
        (  # Exceeds capacity two times, cross over required
            4,
            [create_stream_from_rate(5), create_stream_from_rate(0)],  # 4 in rate
            create_stream_from_rate(1, name="test-stream-please-ignore"),  # 1 exceeding
            [create_stream_from_rate(4), create_stream_from_rate(0)],
        ),
        (  # Exceeds capacity three times, cross over required
            2,
            [create_stream_from_rate(3), create_stream_from_rate(1), create_stream_from_rate(1)],
            create_stream_from_rate(3, name="test-stream-please-ignore"),  # 1 exceeding
            [create_stream_from_rate(2), create_stream_from_rate(0), create_stream_from_rate(0)],
        ),
        (  # Under capacity
            4,
            [create_stream_from_rate(2), create_stream_from_rate(1)],  # 3 in rate, below 4
            create_stream_from_rate(0, name="test-stream-please-ignore"),
            [create_stream_from_rate(2), create_stream_from_rate(1)],
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
        crossover_stream, streams_within_capacity = ConsumerSystem._get_crossover_stream(
            max_rate,
            streams,
            crossover_stream_name="test-stream-please-ignore",
        )
        assert crossover_stream.rate == expected_crossover_stream.rate
        assert [stream_within_capacity.rate for stream_within_capacity in streams_within_capacity] == [
            expected_stream.rate for expected_stream in expected_streams_within_capacity
        ]
