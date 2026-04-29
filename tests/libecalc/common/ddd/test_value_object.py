from dataclasses import FrozenInstanceError, asdict, is_dataclass
from enum import StrEnum

import pytest

from libecalc.common.ddd import value_object


class PressureUnit(StrEnum):
    BARA = "bara"
    BARG = "barg"
    PASCAL = "pascal"


@value_object
class Pressure:
    value: float
    unit: PressureUnit

    def __post_init__(self) -> None:
        """
        Use post init to test business rules for the value object

        Returns:

        """
        if self.value < 0:
            raise ValueError(f"Pressure {self.value} {self.unit} cannot be negative.")


@value_object
class Temperature:
    value_celsius: float

    def __post_init__(self) -> None:
        if self.value_celsius < -273.15:
            raise ValueError(f"Temperature {self.value_celsius}°C is below absolute zero.")


@value_object
class PressureRange:
    """Demonstrates composition/nesting of value objects."""

    low: Pressure
    high: Pressure


class TestIsDataclass:
    def test_subclass_is_a_dataclass(self):
        assert is_dataclass(Pressure)

    def test_instance_is_a_dataclass_instance(self):
        assert is_dataclass(Pressure(value=10.0, unit=PressureUnit.BARA))

    def test_fields_are_accessible(self):
        p = Pressure(value=10.0, unit=PressureUnit.BARA)
        assert p.value == 10.0
        assert p.unit == PressureUnit.BARA

    def test_uses_slots(self):
        assert hasattr(Pressure, "__slots__")
        assert "value" in Pressure.__slots__
        assert "unit" in Pressure.__slots__

    def test_no_instance_dict(self):
        """Slots-based classes have no __dict__ per instance."""
        p = Pressure(value=10.0, unit=PressureUnit.BARA)
        assert not hasattr(p, "__dict__")


class TestImmutability:
    def test_field_reassignment_raises(self):
        p = Pressure(value=10.0, unit=PressureUnit.BARA)
        with pytest.raises(FrozenInstanceError):
            p.value = 99.0  # type: ignore[misc]


class TestEqualityByValue:
    def test_same_values_are_equal(self):
        assert Pressure(value=10.0, unit=PressureUnit.BARA) == Pressure(value=10.0, unit=PressureUnit.BARA)

    def test_different_values_are_not_equal(self):
        assert Pressure(value=10.0, unit=PressureUnit.BARA) != Pressure(value=20.0, unit=PressureUnit.BARA)

    def test_different_units_are_not_equal(self):
        assert Pressure(value=10.0, unit=PressureUnit.BARA) != Pressure(value=10.0, unit=PressureUnit.BARG)

    def test_different_value_object_types_not_equal(self):
        assert Pressure(value=0.0, unit=PressureUnit.BARA) != Temperature(value_celsius=0.0)

    def test_equal_to_itself(self):
        p = Pressure(value=10.0, unit=PressureUnit.BARA)
        assert p == p
        assert p is p  # and is also same instance ...


class TestHashability:
    def test_can_be_used_in_a_set(self):
        p1 = Pressure(value=10.0, unit=PressureUnit.BARA)
        p2 = Pressure(value=10.0, unit=PressureUnit.BARA)
        assert len({p1, p2}) == 1

    def test_distinct_values_distinct_in_set(self):
        assert len({Pressure(10.0, PressureUnit.BARA), Pressure(20.0, PressureUnit.BARA)}) == 2

    def test_distinct_units_distinct_in_set(self):
        assert len({Pressure(10.0, PressureUnit.BARA), Pressure(10.0, PressureUnit.BARG)}) == 2

    def test_can_be_used_as_dict_key(self):
        p = Pressure(value=10.0, unit=PressureUnit.BARA)
        assert {p: "10 bara"}[p] == "10 bara"

    def test_equal_objects_have_same_hash(self):
        assert hash(Pressure(10.0, PressureUnit.BARA)) == hash(Pressure(10.0, PressureUnit.BARA))


class TestPostInitValidation:
    def test_valid_pressure_bara(self):
        assert Pressure(value=100.0, unit=PressureUnit.BARA).value == 100.0

    def test_valid_pressure_barg(self):
        assert Pressure(value=50.0, unit=PressureUnit.BARG).value == 50.0

    def test_valid_pressure_pascal(self):
        assert Pressure(value=101325.0, unit=PressureUnit.PASCAL).value == 101325.0

    def test_negative_bara_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            Pressure(value=-1.0, unit=PressureUnit.BARA)

    def test_negative_barg_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            Pressure(value=-1.0, unit=PressureUnit.BARG)

    def test_negative_pascal_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            Pressure(value=-1.0, unit=PressureUnit.PASCAL)

    def test_zero_pressure_is_valid(self):
        assert Pressure(value=0.0, unit=PressureUnit.BARA).value == 0.0


class TestNestedValueObjects:
    def test_nested_equality(self):
        r1 = PressureRange(low=Pressure(1.0, PressureUnit.BARA), high=Pressure(10.0, PressureUnit.BARA))
        r2 = PressureRange(low=Pressure(1.0, PressureUnit.BARA), high=Pressure(10.0, PressureUnit.BARA))
        assert r1 == r2

    def test_nested_inequality(self):
        r1 = PressureRange(low=Pressure(1.0, PressureUnit.BARA), high=Pressure(10.0, PressureUnit.BARA))
        r2 = PressureRange(low=Pressure(1.0, PressureUnit.BARA), high=Pressure(99.0, PressureUnit.BARA))
        assert r1 != r2

    def test_asdict_flattens_nested(self):
        r = PressureRange(low=Pressure(1.0, PressureUnit.BARA), high=Pressure(10.0, PressureUnit.BARA))
        assert asdict(r) == {
            "low": {"value": 1.0, "unit": "bara"},
            "high": {"value": 10.0, "unit": "bara"},
        }
