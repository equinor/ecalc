import pytest
from libecalc.domain.component_validation_error import (
    DomainValidationException,
    ProcessEqualLengthValidationException,
)
from libecalc.domain.infrastructure.energy_components.turbine import Turbine


class TestTurbine:
    def test_turbine(self):
        Turbine(
            lower_heating_value=38,
            loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
            efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=0,
        )

    def test_unequal_load_and_efficiency_lengths(self):
        with pytest.raises(ProcessEqualLengthValidationException) as e:
            Turbine(
                lower_heating_value=38,
                loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496],
                efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
                energy_usage_adjustment_constant=0,
                energy_usage_adjustment_factor=1.0,
            )
        assert "Need equal number of load and efficiency values for turbine model" in str(e.value)

    def test_invalid_efficiency_fractions(
        self,
        yaml_asset_configuration_service_factory,
        yaml_asset_builder_factory,
        resource_service_factory,
    ):
        """
        Test to validate that the turbine efficiency fractions are within the valid range (0 to 1).

        This test ensures that:
        1. Invalid efficiency fractions (values below 0 or above 1) are correctly identified.
        2. The appropriate exception (DomainValidationException) is raised.
        3. The error message contains the correct details about the invalid values.

        """
        with pytest.raises(DomainValidationException) as e:
            (
                Turbine(
                    lower_heating_value=38,
                    loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
                    efficiency_fractions=[0, 0.138, 0.21, 5.0, 0.286, 0.31, -0.328, 0.342, 0.353, 0.354, 0.36],
                    energy_usage_adjustment_constant=0,
                    energy_usage_adjustment_factor=1,
                ),
            )

        assert "Turbine efficiency fraction should be a number between 0 and 1. Invalid values: [5.0, -0.328]" in str(
            e.value
        )
