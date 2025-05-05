import pytest


from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlEmissionRate, YamlOilVolumeRate


def test_yaml_emission_rate_valid_condition():
    rate = YamlEmissionRate(value="10", condition="x > 5")
    assert rate.condition == "x > 5"
    assert rate.conditions is None


def test_yaml_emission_rate_valid_conditions():
    rate = YamlEmissionRate(value="10", conditions=["x > 5", "y < 10"])
    assert rate.condition is None
    assert rate.conditions == ["x > 5", "y < 10"]


def test_yaml_emission_rate_defaults():
    rate = YamlEmissionRate(value="10")
    assert rate.condition is None
    assert rate.conditions is None


def test_yaml_emission_rate_empty_conditions():
    with pytest.raises(ValueError, match="CONDITIONS cannot be an empty list."):
        YamlEmissionRate(value="10", conditions=[])


def test_yaml_emission_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlEmissionRate(value="10", condition="x > 5", conditions=["x > 5", "y < 10"])


def test_yaml_oil_volume_rate_valid_condition():
    rate = YamlOilVolumeRate(value="10", condition="x > 5")
    assert rate.condition == "x > 5"
    assert rate.conditions is None


def test_yaml_oil_volume_rate_valid_conditions():
    rate = YamlOilVolumeRate(value="10", conditions=["x > 5", "y < 10"])
    assert rate.condition is None
    assert rate.conditions == ["x > 5", "y < 10"]


def test_yaml_oil_volume_rate_defaults():
    rate = YamlOilVolumeRate(value="10")
    assert rate.condition is None
    assert rate.conditions is None


def test_yaml_oil_volume_rate_empty_conditions():
    with pytest.raises(ValueError, match="CONDITIONS cannot be an empty list."):
        YamlOilVolumeRate(value="10", conditions=[])


def test_yaml_oil_volume_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlOilVolumeRate(value="10", condition="x > 5", conditions=["x > 5", "y < 10"])
