from libecalc import dto
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.input.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.input.yaml_keywords import EcalcYamlKeywords


class TestMapFuelType:
    def test_valid_implicit_none_price(self):
        fuel_dict = {EcalcYamlKeywords.name: "diesel"}
        expected_fueltype = dto.types.FuelType(
            name="diesel", price=Expression.setup_from_expression(value=0.0), emissions=[]
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)

    def test_valid_explicit_none_price(self):
        fuel_dict = {EcalcYamlKeywords.name: "diesel", EcalcYamlKeywords.fuel_price: None}
        expected_fueltype = dto.types.FuelType(
            name="diesel", price=Expression.setup_from_expression(value=0.0), emissions=[]
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)

    def test_valid_fuller_fueltype(self):
        fuel_dict = {
            EcalcYamlKeywords.name: "diesel",
            EcalcYamlKeywords.user_defined_tag: FuelTypeUserDefinedCategoryType.DIESEL,
            EcalcYamlKeywords.fuel_price: 1.0,
        }
        expected_fueltype = dto.types.FuelType(
            name="diesel",
            user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
            price=Expression.setup_from_expression(value=1.0),
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)

    def test_valid_full_fueltype(self):
        fuel_dict = {
            EcalcYamlKeywords.name: "diesel",
            EcalcYamlKeywords.user_defined_tag: FuelTypeUserDefinedCategoryType.DIESEL,
            EcalcYamlKeywords.fuel_price: 1.0,
            EcalcYamlKeywords.emissions: [
                {
                    EcalcYamlKeywords.name: "co2",
                    EcalcYamlKeywords.emission_factor: 1.0,
                    EcalcYamlKeywords.emission_quota: 2.2,
                    EcalcYamlKeywords.emission_tax: 2.1,
                }
            ],
        }
        expected_fueltype = dto.types.FuelType(
            name="diesel",
            user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
            price=Expression.setup_from_expression(value=1.0),
            emissions=[
                dto.Emission(
                    name="co2",
                    factor=Expression.setup_from_expression(value=1.0),
                    quota=Expression.setup_from_expression(value=2.2),
                    tax=Expression.setup_from_expression(value=2.1),
                )
            ],
        )

        assert expected_fueltype == FuelMapper.from_yaml_to_dto(fuel_dict)
