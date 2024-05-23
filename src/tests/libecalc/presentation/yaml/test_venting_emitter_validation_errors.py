from pathlib import Path

import pytest
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.fixtures.cases import venting_emitters
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
            emission_rates=[emission_rate],
            regularity=regularity,
            units=[Unit.KILO_PER_DAY.name],
            emission_names=["ch4"],
            rate_types=[RateType.STREAM_DAY],
            emission_keyword_name="EMISSION2",
            names=["Venting emitter 1"],
            path=Path(venting_emitters.__path__[0]),
        )

    assert ("EMISSION2:\tThis is not a valid keyword") in str(exc.value)


def test_wrong_unit_emitters():
    """Test error messages for yaml validation with wrong units."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(DtoValidationError) as exc:
        venting_emitter_yaml_factory(
            emission_rates=[emission_rate],
            regularity=regularity,
            units=[Unit.STANDARD_CUBIC_METER_PER_DAY.name],
            emission_names=["ch4"],
            rate_types=[RateType.STREAM_DAY],
            emission_keyword_name="EMISSIONS",
            names=["Venting emitter 1"],
            path=Path(venting_emitters.__path__[0]),
        )

    assert (
        "\nVenting emitter 1:\nDIRECT_EMISSION.EMISSIONS[0].RATE.UNIT:\tValue error, Unit for venting emitters "
        f"emission rate can not be {Unit.STANDARD_CUBIC_METER_PER_DAY.name}. Allowed units are: "
        f"{Unit.KILO_PER_DAY.name}, {Unit.TONS_PER_DAY.name}."
    ) in str(exc.value)


def test_wrong_unit_format_emitters():
    """Test error messages for yaml validation with wrong unit format."""

    regularity = 0.2
    emission_rate = 10

    with pytest.raises(DtoValidationError) as exc:
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

    assert (
        "\nVenting emitter 1:\nDIRECT_EMISSION.EMISSIONS[0].RATE.UNIT:\tValue error, Unit for venting emitters "
        f"emission rate can not be {Unit.KILO_PER_DAY.value}. Allowed units are: {Unit.KILO_PER_DAY.name}, "
        f"{Unit.TONS_PER_DAY.name}."
    ) in str(exc.value)
