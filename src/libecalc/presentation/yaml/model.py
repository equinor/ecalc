from datetime import datetime
from textwrap import indent
from typing import Dict, List, Optional

from libecalc.common.errors.exceptions import InvalidResource
from libecalc.common.time_utils import Frequency
from libecalc.dto import ResultOptions, VariablesMap
from libecalc.dto.component_graph import ComponentGraph
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto
from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.validation_errors import DtoValidationError, ModelValidationError
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)


class ModelValidationException(Exception):
    def __init__(self, errors: List[ModelValidationError]):
        self._errors = errors
        super().__init__("Model is not valid")

    def error_count(self) -> int:
        return len(self._errors)

    def errors(self) -> List[ModelValidationError]:
        return self._errors

    def __str__(self):
        msg = "Validation error\n\n"
        errors = "\n\n".join(map(str, self._errors))
        errors = indent(errors, "\t")
        msg += errors
        return msg


class YamlModel:
    """
    Class representing both the yaml and the resources.

    We haven't defined a difference in naming between the YamlModel representing only the yaml file and this class,
    which also have information about the referenced resources.

    Maybe we could use 'configuration' for the single yaml file, that naming is already used a lot for the instantiation
    of that YamlModel class.

    configuration: the model configuration
    resources: the model 'input', kind of
    model: configuration + resources (input)
    """

    def __init__(
        self,
        configuration_service: ConfigurationService,
        resource_service: ResourceService,
        output_frequency: Frequency,
    ) -> None:
        self._output_frequency = output_frequency
        self._configuration = configuration_service.get_configuration()
        self.resources = resource_service.get_resources(self._configuration)
        self.is_valid_for_run()
        self.dto = map_yaml_to_dto(configuration=self._configuration, resources=self.resources)

    @property
    def start(self) -> Optional[datetime]:
        return self._configuration.start

    @property
    def end(self) -> Optional[datetime]:
        return self._configuration.end

    @property
    def variables(self) -> VariablesMap:
        return map_yaml_to_variables(
            configuration=self._configuration, resources=self.resources, result_options=self.result_options
        )

    @property
    def result_options(self) -> ResultOptions:
        return ResultOptions(
            start=self._configuration.start,
            end=self._configuration.end,
            output_frequency=self._output_frequency,
        )

    @property
    def graph(self) -> ComponentGraph:
        return self.dto.get_graph()

    def _find_resource_from_name(self, filename: str) -> Optional[Resource]:
        return self.resources.get(filename)

    def _get_token_references(self, yaml_model: YamlValidator) -> List[str]:
        token_references = []
        for time_series in yaml_model.time_series:
            resource = self._find_resource_from_name(time_series.file)

            if resource is None:
                # Don't add any tokens if the resource is not found
                continue

            try:
                headers = resource.get_headers()
                for header in headers:
                    token_references.append(f"{time_series.name};{header}")
            except InvalidResource:
                # Don't add any tokens if resource is invalid (unable to read header)
                continue

        for reference in yaml_model.variables:
            token_references.append(f"$var.{reference}")

        return token_references

    @staticmethod
    def _get_model_types(yaml_model: YamlValidator) -> Dict["ModelName", "ModelContext"]:
        models = [*yaml_model.models, *yaml_model.facility_inputs]
        model_types: Dict[ModelName, ModelContext] = {}
        for model in models:
            if hasattr(model, "name"):
                model_types[model.name] = model
        return model_types

    def _get_validation_context(self, yaml_model: YamlValidator) -> YamlModelValidationContext:
        return {
            YamlModelValidationContextNames.resource_file_names: [name for name, resource in self.resources.items()],
            YamlModelValidationContextNames.expression_tokens: self._get_token_references(yaml_model=yaml_model),
            YamlModelValidationContextNames.model_types: self._get_model_types(yaml_model=yaml_model),
        }

    def is_valid_for_run(self) -> bool:
        try:
            # Validate model
            validation_context = self._get_validation_context(yaml_model=self._configuration)
            self._configuration.validate(validation_context)
            return True
        except DtoValidationError as e:
            raise ModelValidationException(errors=e.errors()) from e
