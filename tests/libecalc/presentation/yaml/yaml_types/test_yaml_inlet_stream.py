import pytest
from pydantic import ValidationError

from libecalc.common.utils.rates import RateType
from libecalc.testing.process_builders import YamlInletStreamRateBuilder


def test_yaml_inlet_stream_rate_defaults_to_stream_day():
    rate = YamlInletStreamRateBuilder().with_value(1000.0).with_unit("SM3_PER_DAY").validate()
    assert rate.type == RateType.STREAM_DAY


def test_yaml_inlet_stream_rate_accepts_stream_day():
    rate = (
        YamlInletStreamRateBuilder()
        .with_value(1000.0)
        .with_unit("SM3_PER_DAY")
        .with_type(RateType.STREAM_DAY)
        .validate()
    )
    assert rate.type == RateType.STREAM_DAY


def test_yaml_inlet_stream_rate_rejects_calendar_day():
    with pytest.raises(ValidationError):
        YamlInletStreamRateBuilder().with_value(1000.0).with_unit("SM3_PER_DAY").with_type(
            RateType.CALENDAR_DAY
        ).validate()
