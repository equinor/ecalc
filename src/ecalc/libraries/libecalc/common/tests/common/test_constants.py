from libecalc.common.units import UnitConstants


def test_earth_gravity():
    assert UnitConstants.EARTH_GRAVITY == 9.81


def test_standard_pressure():
    assert UnitConstants.STANDARD_PRESSURE_BARA == 1.01325


def test_standard_temperature_celsius():
    assert UnitConstants.STANDARD_TEMPERATURE_CELSIUS == 15.0


def test_standard_temperature_kelvin():
    assert UnitConstants.STANDARD_TEMPERATURE_KELVIN == 288.15


def test__celsius_to_kelvin():
    assert UnitConstants.CELSIUS_TO_KELVIN == 273.15


def test_hours_per_day():
    assert UnitConstants.HOURS_PER_DAY == 24.0


def test_gas_constant():
    assert UnitConstants.GAS_CONSTANT == 8.314472


def test_seconds_per_hour():
    assert UnitConstants.SECONDS_PER_HOUR == 3600.0
