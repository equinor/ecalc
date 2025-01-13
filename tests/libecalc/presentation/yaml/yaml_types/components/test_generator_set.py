import pytest

from libecalc.testing.yaml_builder import YamlGeneratorSetBuilder


class TestGeneratorSet:
    def test_power_from_shore_wrong_category(self):
        """
        Check that CABLE_LOSS and MAX_USAGE_FROM_SHORE are only allowed if generator set category is POWER-FROM-SHORE
        This validation is done in the yaml layer.
        """

        # Check for CABLE_LOSS
        with pytest.raises(ValueError) as exc_info:
            YamlGeneratorSetBuilder().with_test_data().with_category("BOILER").with_cable_loss(0).validate()

        assert ("CABLE_LOSS is only valid for the category POWER-FROM-SHORE, not for BOILER") in str(exc_info.value)

        # Check for MAX_USAGE_FROM_SHORE
        with pytest.raises(ValueError) as exc_info:
            YamlGeneratorSetBuilder().with_test_data().with_category("BOILER").with_max_usage_from_shore(20).validate()

        assert ("MAX_USAGE_FROM_SHORE is only valid for the category POWER-FROM-SHORE, not for BOILER") in str(
            exc_info.value
        )

        # Check for CABLE_LOSS and MAX_USAGE_FROM_SHORE
        with pytest.raises(ValueError) as exc_info:
            (
                YamlGeneratorSetBuilder()
                .with_test_data()
                .with_category("BOILER")
                .with_cable_loss(0)
                .with_max_usage_from_shore(20)
            ).validate()

        assert (
            "CABLE_LOSS and MAX_USAGE_FROM_SHORE are only valid for the category POWER-FROM-SHORE, not for BOILER"
        ) in str(exc_info.value)
