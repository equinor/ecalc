from pydantic import ValidationError

from libecalc.dto import Emission, FuelType
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType


class FuelMapper:
    @staticmethod
    def from_yaml_to_dto(fuel: YamlFuelType) -> FuelType:
        try:
            return FuelType(
                name=fuel.name,
                user_defined_category=fuel.category,
                emissions=[
                    Emission(
                        name=emission.name,
                        factor=emission.factor,
                    )
                    for emission in fuel.emissions
                ],
            )
        except ValidationError as e:
            raise DtoValidationError(data=fuel.model_dump(), validation_error=e) from e
