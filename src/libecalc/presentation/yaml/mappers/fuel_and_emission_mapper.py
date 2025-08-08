from uuid import uuid4

from pydantic import ValidationError

from libecalc.domain.component_validation_error import ComponentValidationException, ModelValidationError
from libecalc.dto import Emission, FuelType
from libecalc.expression.expression import InvalidExpressionError
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.validation_errors import DtoValidationError, Location
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType


class FuelMapper:
    def __init__(self, configuration: YamlValidator):
        self._configuration = configuration

    def from_yaml_to_dto(self, fuel: YamlFuelType, fuel_index: int) -> FuelType:
        fuel_types_yaml_path = YamlPath(keys=("FUEL_TYPES",))

        def create_error(message: str, fuel_name: str) -> ModelValidationError:
            fuel_yaml_path = fuel_types_yaml_path.append(fuel_index)
            file_context = self._configuration.get_file_context(fuel_yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=Location(keys=("FUEL_TYPES", fuel_name)),
                name=fuel_name,
                file_context=file_context,
            )

        try:
            return FuelType(
                id=uuid4(),
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
        except InvalidExpressionError as e:
            raise ComponentValidationException(errors=[create_error(str(e), fuel.name)]) from e
