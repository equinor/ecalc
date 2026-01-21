"""Tests for YamlShaft model type."""

import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_types.models.yaml_shaft import YamlShaft


class TestYamlShaft:
    """Test YamlShaft Pydantic model."""

    def test_valid_shaft_model(self):
        """Test creating a valid shaft model."""
        shaft = YamlShaft(
            name="my_shaft",
            type=YamlModelType.SHAFT,
            mechanical_efficiency=0.95,
        )
        assert shaft.name == "my_shaft"
        assert shaft.type == YamlModelType.SHAFT
        assert shaft.mechanical_efficiency == 0.95

    def test_shaft_type_is_shaft(self):
        """Test that shaft type is SHAFT."""
        shaft = YamlShaft(
            name="test_shaft",
            type="SHAFT",
            mechanical_efficiency=0.9,
        )
        assert shaft.type == YamlModelType.SHAFT
        assert shaft.type.value == "SHAFT"

    def test_shaft_mechanical_efficiency_at_boundary(self):
        """Test shaft with mechanical efficiency at 1.0 boundary."""
        shaft = YamlShaft(
            name="perfect_shaft",
            type="SHAFT",
            mechanical_efficiency=1.0,
        )
        assert shaft.mechanical_efficiency == 1.0

    def test_shaft_low_mechanical_efficiency(self):
        """Test shaft with low but valid mechanical efficiency."""
        shaft = YamlShaft(
            name="lossy_shaft",
            type="SHAFT",
            mechanical_efficiency=0.5,
        )
        assert shaft.mechanical_efficiency == 0.5

    def test_shaft_requires_mechanical_efficiency(self):
        """Test that mechanical_efficiency is required."""
        with pytest.raises(ValidationError, match="MECHANICAL_EFFICIENCY"):
            YamlShaft(
                name="missing_efficiency",
                type="SHAFT",
                # mechanical_efficiency not provided
            )

    @pytest.mark.parametrize(
        "efficiency,reason",
        [
            (0.0, "zero"),
            (-0.1, "negative"),
            (1.1, "above 1.0"),
        ],
    )
    def test_shaft_efficiency_invalid_values(self, efficiency, reason):
        """Test that invalid mechanical efficiency values are rejected."""
        with pytest.raises(ValidationError):
            YamlShaft(
                name="invalid_shaft",
                type="SHAFT",
                mechanical_efficiency=efficiency,
            )
