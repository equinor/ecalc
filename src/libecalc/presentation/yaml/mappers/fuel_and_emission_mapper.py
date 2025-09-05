from uuid import uuid4

from pydantic import ValidationError

from libecalc.dto import Emission, FuelType
from libecalc.expression.expression import InvalidExpressionError
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType


class FuelMapper:
    def __init__(self, configuration: YamlValidator):
        self._configuration = configuration

    def from_yaml_to_dto(self, fuel: YamlFuelType, fuel_index: int) -> FuelType:
        fuel_types_yaml_path = YamlPath(keys=("FUEL_TYPES",))
        fuel_yaml_path = fuel_types_yaml_path.append(fuel_index)

        def create_error(message: str, fuel_name: str) -> ModelValidationError:
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
            raise ModelValidationException.from_pydantic(
                e, file_context=self._configuration.get_file_context(fuel_yaml_path.keys)
            ) from e
        except InvalidExpressionError as e:
            raise ModelValidationException(errors=[create_error(str(e), fuel.name)]) from e
