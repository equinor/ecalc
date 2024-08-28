from pathlib import Path

import pytest

from libecalc.common.utils.rates import RateType
from libecalc.fixtures.cases import venting_emitters
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import (
    venting_emitter_yaml_factory,
)
from libecalc.presentation.yaml.model import ModelValidationException
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRateUnits,
    YamlOilRateUnits,
)


def test_wrong_keyword_name_emitters():
    """Test custom pydantic error messages for yaml validation of missing mandatory keywords."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(ModelValidationException) as exc:
        venting_emitter_yaml_factory(
            emission_rates=[emission_rate],
            regularity=regularity,
            units=[YamlEmissionRateUnits.KILO_PER_DAY],
            emission_names=["ch4"],
            rate_types=[RateType.STREAM_DAY],
            emission_keyword_name="EMISSION2",
            names=["Venting emitter 1"],
            path=Path(venting_emitters.__path__[0]),
        )

    error_message = str(exc.value)

    assert "EMISSION2" in error_message
    assert "This is not a valid keyword" in error_message


def test_wrong_unit_emitters():
    """Test error messages for yaml validation with wrong units."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(ModelValidationException) as exc:
        venting_emitter_yaml_factory(
            emission_rates=[emission_rate],
            regularity=regularity,
            units=[YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY],
            emission_names=["ch4"],
            rate_types=[RateType.STREAM_DAY],
            emission_keyword_name="EMISSIONS",
            names=["Venting emitter 1"],
            path=Path(venting_emitters.__path__[0]),
        )

    error_message = str(exc.value)

    assert "Venting emitter 1" in error_message
    assert "DIRECT_EMISSION.EMISSIONS[0].RATE.UNIT" in error_message
    assert (
        f"Input should be '{YamlEmissionRateUnits.KILO_PER_DAY.value}' or '{YamlEmissionRateUnits.TONS_PER_DAY.value}'"
        in error_message
    )


def test_wrong_unit_format_emitters():
    """Test error messages for yaml validation with wrong unit format."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(ModelValidationException) as exc:
        venting_emitter_yaml_factory(
            emission_rates=[emission_rate],
            regularity=regularity,
            units=["kg/d"],
            emission_names=["ch4"],
            rate_types=[RateType.STREAM_DAY],
            emission_keyword_name="EMISSIONS",
            names=["Venting emitter 1"],
            path=Path(venting_emitters.__path__[0]),
        )

    error_message = str(exc.value)

    assert "Venting emitter 1" in error_message
    assert "DIRECT_EMISSION.EMISSIONS[0].RATE.UNIT" in error_message
    assert (
        f"Input should be '{YamlEmissionRateUnits.KILO_PER_DAY.value}' or '{YamlEmissionRateUnits.TONS_PER_DAY.value}'"
        in error_message
    )
