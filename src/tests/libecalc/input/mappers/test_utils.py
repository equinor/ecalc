from dataclasses import dataclass
from typing import List

from libecalc.common.units import Unit
from libecalc.presentation.yaml.mappers.consumer_function_mapper import _map_condition
from libecalc.presentation.yaml.mappers.utils import (
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_head_to_meter_liquid_column,
    convert_rate_to_am3_per_hour,
    convert_temperature_to_kelvin,
)


@dataclass
class ConditionedModel:
    condition: str = None
    conditions: List[str] = None


class TestMapCondition:
    def test_valid_single(self):
        condition = "5 {+} SIM1;COL1"
        assert condition == _map_condition(ConditionedModel(condition=condition))

    def test_valid_multiple(self):
        conditions = [
            "5 {+} SIM1;COL1",
            "6 {+} SIM1;COL2",
        ]
        assert f"({conditions[0]}) {{*}} ({conditions[1]})" == _map_condition(ConditionedModel(conditions=conditions))

    def test_valid_multiple_with_single_item(self):
        conditions = [
            "5 {+} SIM1;COL1",
        ]
        assert f"({conditions[0]})" == _map_condition(ConditionedModel(conditions=conditions))


def test_convert_rate_to_am3_per_hour():
    """Only Am3/hour available for now."""
    result = convert_rate_to_am3_per_hour(rate_values=[1, 2, 3], input_unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR)
    assert result == [1, 2, 3]


def test_convert_head_to_joule_per_kg():
    result = convert_head_to_joule_per_kg(head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG)
    assert result == [1000, 2000, 3000]

    result = convert_head_to_joule_per_kg(head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG)
    assert result == [1, 2, 3]

    result = convert_head_to_joule_per_kg(head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN)
    assert result == [9.81, 9.81 * 2, 9.81 * 3]


def test_convert_head_to_meter_liquid_column():
    result = convert_head_to_meter_liquid_column(
        head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG
    )
    assert result == [1000 / 9.81, 2000 / 9.81, 3000 / 9.81]

    result = convert_head_to_meter_liquid_column(head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG)
    assert result == [1 / 9.81, 2 / 9.81, 3 / 9.81]

    result = convert_head_to_meter_liquid_column(
        head_values=[1, 2, 3], input_unit=Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN
    )
    assert result == [1, 2, 3]


def test_convert_temperature_to_kelvin():
    result = convert_temperature_to_kelvin(temperature_values=[1, 2, 3], input_unit=Unit.KELVIN)
    assert result == [1, 2, 3]

    result = convert_temperature_to_kelvin(temperature_values=[1, 2, 3], input_unit=Unit.CELSIUS)
    assert result == [274.15, 275.15, 276.15]


def test_convert_efficiency_to_fraction():
    result = convert_efficiency_to_fraction(efficiency_values=[1, 2, 3], input_unit=Unit.FRACTION)
    assert result == [1, 2, 3]

    result = convert_efficiency_to_fraction(efficiency_values=[1, 2, 3], input_unit=Unit.PERCENTAGE)
    assert result == [0.01, 0.02, 0.03]
