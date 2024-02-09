import pytest
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import (
    venting_emitter_yaml_factory,
)
from libecalc.presentation.yaml.validation_errors import DtoValidationError


def test_wrong_keyword_name_emitters():
    """Test custom pydantic error messages for yaml validation of missing mandatory keywords."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(DtoValidationError) as exc:
        venting_emitter_yaml_factory(
            emission_rate=emission_rate,
            regularity=regularity,
            unit=Unit.KILO_PER_DAY,
            emission_name="ch4",
            rate_type=RateType.STREAM_DAY,
            emission_keyword_name="EMISSION2",
            name="Venting emitter 1",
        )

    assert "Venting emitter 1:\nEMISSION:\tThis keyword is missing, it is required" in str(exc.value)
    assert "EMISSION2:\tThis is not a valid keyword" in str(exc.value)


def test_wrong_unit_emitters():
    """Test custom pydantic error messages for yaml validation with wrong units."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(DtoValidationError) as exc:
        venting_emitter_yaml_factory(
            emission_rate=emission_rate,
            regularity=regularity,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            emission_name="ch4",
            rate_type=RateType.STREAM_DAY,
            emission_keyword_name="EMISSION",
            name="Venting emitter 1",
        )

    assert "Venting emitter 1:\nInput should be <Unit.KILO_PER_DAY: 'kg/d'> or <Unit.TONS_PER_DAY: 't/d'>" in str(
        exc.value
    )
