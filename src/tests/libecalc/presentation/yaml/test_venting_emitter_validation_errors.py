from io import StringIO

import pytest
from pydantic import ValidationError

from libecalc.common.time_utils import Frequency
from libecalc.common.utils.rates import RateType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlVentingEmission,
    YamlVentingType,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlEmissionRateUnits,
    YamlOilRateUnits,
)


def test_wrong_keyword_name(resource_service_factory, configuration_service_factory):
    """Test custom pydantic error message for invalid keyword names."""
    model = YamlModel(
        configuration_service=configuration_service_factory(
            ResourceStream(stream=StringIO("INVALID_KEYWORD_IN_YAML: 5"), name="INVALID_MODEL")
        ),
        resource_service=resource_service_factory({}),
        output_frequency=Frequency.NONE,
    )
    with pytest.raises(ModelValidationException) as exc:
        model.validate_for_run()

    errors = exc.value.errors()
    assert "INVALID_KEYWORD_IN_YAML" in str(exc.value)
    invalid_keyword_error = next(
        error for error in errors if error.location == Location(keys=["INVALID_KEYWORD_IN_YAML"])
    )

    assert invalid_keyword_error.message == "This is not a valid keyword"


def test_wrong_unit_emitters():
    """Ensure units are constrained for venting emitter"""

    with pytest.raises(ValidationError) as exc:
        YamlDirectTypeEmitter(
            name="Venting emitter 1",
            category=ConsumerUserDefinedCategoryType.STORAGE,
            type=YamlVentingType.DIRECT_EMISSION,
            emissions=[
                YamlVentingEmission(
                    name="ch4",
                    rate=YamlEmissionRate(
                        value=10,
                        unit=YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                )
            ],
        )

    error_message = str(exc.value)

    assert len(exc.value.errors()) == 1

    assert (
        f"Input should be '{YamlEmissionRateUnits.KILO_PER_DAY.value}' or '{YamlEmissionRateUnits.TONS_PER_DAY.value}'"
        in error_message
    )


def test_wrong_unit_format_emitters():
    """Ensure we don't accept the 'old' unit format for venting emitters"""

    with pytest.raises(ValidationError) as exc:
        YamlDirectTypeEmitter(
            name="Venting emitter 1",
            category=ConsumerUserDefinedCategoryType.STORAGE,
            type=YamlVentingType.DIRECT_EMISSION,
            emissions=[
                YamlVentingEmission(
                    name="ch4",
                    rate=YamlEmissionRate(
                        value=10,
                        unit="kg/d",
                        type=RateType.STREAM_DAY,
                    ),
                )
            ],
        )

    error_message = str(exc.value)
    assert len(exc.value.errors()) == 1

    assert (
        f"Input should be '{YamlEmissionRateUnits.KILO_PER_DAY.value}' or '{YamlEmissionRateUnits.TONS_PER_DAY.value}'"
        in error_message
    )
