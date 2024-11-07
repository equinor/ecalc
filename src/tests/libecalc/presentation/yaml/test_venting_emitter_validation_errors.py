import pytest
from pydantic import ValidationError

from libecalc.common.utils.rates import RateType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
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
