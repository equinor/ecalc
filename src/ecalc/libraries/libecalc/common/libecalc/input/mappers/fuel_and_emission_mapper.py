from typing import Dict

from libecalc import dto
from libecalc.input.validation_errors import DtoValidationError
from libecalc.input.yaml_keywords import EcalcYamlKeywords
from pydantic import ValidationError


class EmissionMapper:
    @staticmethod
    def from_yaml_to_dto(data: Dict) -> dto.Emission:
        return dto.Emission(
            name=data.get(EcalcYamlKeywords.name),
            factor=data.get(EcalcYamlKeywords.emission_factor),
            tax=data.get(EcalcYamlKeywords.emission_tax),
            quota=data.get(EcalcYamlKeywords.emission_quota),
        )


class FuelMapper:
    @staticmethod
    def from_yaml_to_dto(fuel: Dict) -> dto.types.FuelType:
        try:
            return dto.types.FuelType(
                name=fuel.get(EcalcYamlKeywords.name),
                user_defined_category=fuel.get(EcalcYamlKeywords.user_defined_tag),
                price=fuel.get(EcalcYamlKeywords.fuel_price),
                emissions=[
                    EmissionMapper.from_yaml_to_dto(emission) for emission in fuel.get(EcalcYamlKeywords.emissions, [])
                ],
            )
        except ValidationError as e:
            raise DtoValidationError(data=fuel, validation_error=e) from e
