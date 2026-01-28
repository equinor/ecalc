from uuid import uuid4

import pytest
from inline_snapshot import snapshot
from libecalc.application.common_stream_distribution import CommonStreamDistribution, HasCapacity, Overflow
from libecalc.domain.component_validation_error import DomainValidationException


class Item(HasCapacity):
    def __init__(self, capacity: float):
        self.id = uuid4()
        self._capacity = capacity

    def get_unhandled_rate(self, rate: float, pressure: float) -> float:
        return max(0.0, rate - self._capacity)


class TestCommonStreamDistribution:
    def test_common_stream_without_overflow(self, stream_factory, fluid_service):
        inlet_stream = stream_factory(standard_rate_m3_per_day=100)
        items = [
            Item(capacity=5),
            Item(capacity=5),
        ]
        stream_distribution = CommonStreamDistribution(
            inlet_stream=inlet_stream,
            items={item.id: item for item in items},
            rate_fractions=[0.5, 0.5],
            overflows=[],
            fluid_service=fluid_service,
        )

        streams = stream_distribution.get_streams()

        rates = [stream.standard_rate_sm3_per_day for stream in streams]
        assert rates == [50, 50]

    def test_common_stream_with_overflow(self, stream_factory, fluid_service):
        inlet_stream = stream_factory(standard_rate_m3_per_day=100)
        items = [
            Item(capacity=45),
            Item(capacity=55),
        ]
        stream_distribution = CommonStreamDistribution(
            inlet_stream=inlet_stream,
            items={item.id: item for item in items},
            rate_fractions=[0.5, 0.5],
            overflows=[Overflow(from_id=items[0].id, to_id=items[1].id)],
            fluid_service=fluid_service,
        )

        streams = stream_distribution.get_streams()

        rates = [stream.standard_rate_sm3_per_day for stream in streams]
        assert rates == [45, 55]

    def test_common_stream_with_overflow_out_of_capacity(self, stream_factory, fluid_service):
        inlet_stream = stream_factory(standard_rate_m3_per_day=110)
        items = [
            Item(capacity=45),
            Item(capacity=55),
        ]
        stream_distribution = CommonStreamDistribution(
            inlet_stream=inlet_stream,
            items={item.id: item for item in items},
            rate_fractions=[0.5, 0.5],
            overflows=[Overflow(from_id=items[0].id, to_id=items[1].id)],
            fluid_service=fluid_service,
        )

        streams = stream_distribution.get_streams()

        rates = [stream.standard_rate_sm3_per_day for stream in streams]
        assert rates == [45, 65]

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_common_stream_with_overflow_cycle(self, stream_factory, fluid_service):
        inlet_stream = stream_factory(standard_rate_m3_per_day=100)
        items = [
            Item(capacity=45),
            Item(capacity=55),
        ]
        with pytest.raises(DomainValidationException) as exc_info:
            CommonStreamDistribution(
                inlet_stream=inlet_stream,
                items={item.id: item for item in items},
                rate_fractions=[0.5, 0.5],
                overflows=[
                    Overflow(from_id=items[0].id, to_id=items[1].id),
                    Overflow(from_id=items[1].id, to_id=items[0].id),
                ],
                fluid_service=fluid_service,
            )

        assert str(exc_info.value) == snapshot("Overflow can not be cyclic")
