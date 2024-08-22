import numpy as np
import pytest

from libecalc.common import units
from libecalc.common.units import Unit

test_data = [
    # from_unit, to_unit, value, expected_result
    (units.Unit.TONS_PER_DAY, units.Unit.KILO_PER_DAY, 1.0, 1000.0),
    (units.Unit.KILO_PER_DAY, units.Unit.TONS_PER_DAY, 1.0, 0.001),
    (units.Unit.KILO_PER_DAY, units.Unit.TONS_PER_DAY, 1000.0, 1.0),
    (units.Unit.TONS_PER_DAY, units.Unit.KILO_PER_DAY, 0.001, 1.0),
    (units.Unit.KILO_PER_DAY, units.Unit.TONS_PER_DAY, -1000.0, -1.0),
    (units.Unit.KILO_PER_DAY, units.Unit.TONS_PER_DAY, 0.0, 0.0),
    (units.Unit.TONS_PER_DAY, units.Unit.KILO_PER_DAY, -1.0, -1000.0),
    (units.Unit.TONS_PER_DAY, units.Unit.TONS_PER_DAY, 1000.0, 1000.0),
    (units.Unit.TONS_PER_DAY, units.Unit.TONS_PER_DAY, 0.0, 0.0),
    (units.Unit.TONS_PER_DAY, units.Unit.TONS_PER_DAY, -1.0, -1.0),
    (units.Unit.TONS, units.Unit.KILO, 1.0, 1000.0),
    (units.Unit.KILO, units.Unit.TONS, 1.0, 0.001),
    (units.Unit.KILO, units.Unit.TONS, 1000.0, 1.0),
    (units.Unit.TONS, units.Unit.KILO, 0.001, 1.0),
    (units.Unit.KILO, units.Unit.TONS, -1000.0, -1.0),
    (units.Unit.KILO, units.Unit.TONS, 0.0, 0.0),
    (units.Unit.TONS, units.Unit.KILO, -1.0, -1000.0),
    (units.Unit.TONS, units.Unit.TONS, 1000.0, 1000.0),
    (units.Unit.TONS, units.Unit.TONS, 0.0, 0.0),
    (units.Unit.TONS, units.Unit.TONS, -1.0, -1.0),
    (units.Unit.CELSIUS, units.Unit.KELVIN, 100, 373.15),
    (units.Unit.KELVIN, units.Unit.CELSIUS, 373.15, 100),
    (units.Unit.PERCENTAGE, units.Unit.FRACTION, 100, 1),
    (units.Unit.PERCENTAGE, units.Unit.FRACTION, 0, 0),
    (units.Unit.FRACTION, units.Unit.PERCENTAGE, 1, 100),
    (units.Unit.FRACTION, units.Unit.PERCENTAGE, 0, 0),
    (units.Unit.POLYTROPIC_HEAD_JOULE_PER_KG, units.Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG, 1000, 1),
    (units.Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG, units.Unit.POLYTROPIC_HEAD_JOULE_PER_KG, 1, 1000),
    (units.Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN, units.Unit.POLYTROPIC_HEAD_JOULE_PER_KG, 1, 9.81),
    (units.Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN, units.Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG, 1000, 9.81),
    (units.Unit.POLYTROPIC_HEAD_JOULE_PER_KG, units.Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN, 9.81, 1),
    (units.Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG, units.Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN, 9.81, 1000),
    (units.Unit.KILO_PASCAL, units.Unit.BARA, 100, 1),
    (units.Unit.BARA, units.Unit.KILO_PASCAL, 1, 100),
    (units.Unit.PASCAL, units.Unit.BARA, 1e5, 1),
    (units.Unit.BARA, units.Unit.PASCAL, 1, 1e5),
    (units.Unit.BOE, units.Unit.STANDARD_CUBIC_METER, 6.29, 1),
    (units.Unit.STANDARD_CUBIC_METER, units.Unit.BOE, 1, 6.29),
]


@pytest.mark.parametrize("from_unit, to_unit, value, expected_result", test_data)
def test_simple_unit_conversion(from_unit: units.Unit, to_unit: units.Unit, value: float, expected_result: float):
    assert from_unit.to(to_unit)(value) == expected_result


def test_missing_conversions():
    with pytest.raises(NotImplementedError) as ne:
        units.Unit.GIGA_WATT_HOURS.to(units.Unit.STANDARD_CUBIC_METER)(1.0)
    assert (
        f"The conversion between {units.Unit.GIGA_WATT_HOURS.value} to {units.Unit.STANDARD_CUBIC_METER.value} has not been added to unit conversion registry."
        in str(ne)
    )


def test_verify_unit():
    """The other tests should verify this, and it will most likely fail runtime, but
    this test just initializes Unit Enum. If a new enum value has been added with incorrect
    parameters, this will fail.
    """
    assert Unit


def test_unit_conversion_int():
    result = units.Unit.TONS_PER_DAY.to(units.Unit.KILO_PER_DAY)(1)
    assert isinstance(result, int)
    assert result == 1000


def test_unit_conversion_float():
    result = units.Unit.TONS_PER_DAY.to(units.Unit.KILO_PER_DAY)(1.5)
    assert isinstance(result, float)
    assert result == 1500


def test_unit_conversion_numpy_array():
    result = units.Unit.TONS_PER_DAY.to(units.Unit.KILO_PER_DAY)(np.array([1, 2, 3, 4, 5]))
    assert isinstance(result, np.ndarray)
    assert list(result) == [1000, 2000, 3000, 4000, 5000]


def test_unit_conversion_list_array():
    result = units.Unit.TONS_PER_DAY.to(units.Unit.KILO_PER_DAY)([1, 2, 3, 4, 5])
    assert isinstance(result, list)
    assert list(result) == [1000, 2000, 3000, 4000, 5000]
