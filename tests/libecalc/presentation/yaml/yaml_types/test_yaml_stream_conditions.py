import pytest

from libecalc.testing.yaml_builder import YamlEmissionRateBuilder, YamlOilVolumeRateBuilder


def test_yaml_emission_rate_valid_condition():
    rate = YamlEmissionRateBuilder().with_value(10).with_condition("x > 5").validate()

    assert rate.condition == "x > 5"
    assert rate.conditions is None


def test_yaml_emission_rate_valid_conditions():
    rate = YamlEmissionRateBuilder().with_value(10).with_conditions(["x > 5", "y < 10"]).validate()

    assert rate.condition is None
    assert rate.conditions == ["x > 5", "y < 10"]


def test_yaml_emission_rate_defaults():
    rate = YamlEmissionRateBuilder().with_value(10)
    assert rate.condition is None
    assert rate.conditions is None


def test_yaml_emission_rate_empty_conditions():
    with pytest.raises(ValueError, match="CONDITIONS cannot be an empty list."):
        YamlEmissionRateBuilder().with_value(10).with_conditions([]).validate()


def test_yaml_emission_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlEmissionRateBuilder().with_value(10).with_condition("x > 5").with_conditions(["x > 5", "y < 10"]).validate()


def test_yaml_oil_volume_rate_valid_condition():
    rate = YamlOilVolumeRateBuilder().with_value(10).with_condition("x > 5").validate()
    assert rate.condition == "x > 5"
    assert rate.conditions is None


def test_yaml_oil_volume_rate_valid_conditions():
    rate = YamlOilVolumeRateBuilder().with_value(10).with_conditions(["x > 5", "y < 10"]).validate()

    assert rate.condition is None
    assert rate.conditions == ["x > 5", "y < 10"]


def test_yaml_oil_volume_rate_defaults():
    rate = YamlOilVolumeRateBuilder().with_value(10).validate()
    assert rate.condition is None
    assert rate.conditions is None


def test_yaml_oil_volume_rate_empty_conditions():
    with pytest.raises(ValueError, match="CONDITIONS cannot be an empty list."):
        YamlOilVolumeRateBuilder().with_value(10).with_conditions([]).validate()


def test_yaml_oil_volume_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlOilVolumeRateBuilder().with_value(10).with_condition("x > 5").with_conditions(
            ["x > 5", "y < 10"]
        ).validate()
