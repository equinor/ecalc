import libecalc.dto.fuel_type
from libecalc import dto
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


class TestMapFuelType:
    def test_valid_implicit(self):
        fuel_dict = {EcalcYamlKeywords.name: "diesel"}
        expected_fueltype = libecalc.dto.fuel_type.FuelType(name="diesel", emissions=[])

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)

    def test_valid_fuller_fueltype(self):
        fuel_dict = {
            EcalcYamlKeywords.name: "diesel",
            EcalcYamlKeywords.user_defined_tag: FuelTypeUserDefinedCategoryType.DIESEL,
        }
        expected_fueltype = libecalc.dto.fuel_type.FuelType(
            name="diesel",
            user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)

    def test_valid_full_fueltype(self):
        fuel_dict = {
            EcalcYamlKeywords.name: "diesel",
            EcalcYamlKeywords.user_defined_tag: FuelTypeUserDefinedCategoryType.DIESEL,
            EcalcYamlKeywords.emissions: [
                {
                    EcalcYamlKeywords.name: "co2",
                    EcalcYamlKeywords.emission_factor: 1.0,
                }
            ],
        }
        expected_fueltype = libecalc.dto.fuel_type.FuelType(
            name="diesel",
            user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
            emissions=[
                dto.Emission(
                    name="co2",
                    factor=Expression.setup_from_expression(value=1.0),
                )
            ],
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)
