import abc
from datetime import datetime
from pathlib import Path
from textwrap import indent
from typing import Callable, Dict, List, Optional, Protocol

from libecalc.common.errors.exceptions import EcalcError, InvalidResourceHeaderException
from libecalc.common.logger import logger
from libecalc.common.time_utils import Frequency, Period
from libecalc.dto import Asset, ResultOptions, VariablesMap
from libecalc.dto.component_graph import ComponentGraph
from libecalc.infrastructure.file_io import (
    read_facility_resource,
    read_timeseries_resource,
)
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto
from libecalc.presentation.yaml.validation_errors import DtoValidationError, ModelValidationError
from libecalc.presentation.yaml.yaml_entities import (
    Resource,
    ResourceStream,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)


class ResourceService(Protocol):
    @abc.abstractmethod
    def get_resources(self, configuration: YamlValidator) -> Dict[str, Resource]: ...


class ConfigurationService(Protocol):
    @abc.abstractmethod
    def get_configuration(self) -> YamlValidator: ...


class FileResourceService(ResourceService):
    def __init__(self, working_directory: Path):
        self._working_directory = working_directory

    @staticmethod
    def _read_resource(resource_name: Path, *args, read_func: Callable[..., Resource]):
        try:
            return read_func(resource_name, *args)
        except (InvalidResourceHeaderException, ValueError) as exc:
            logger.error(str(exc))
            raise EcalcError("Failed to read resource", f"Failed to read {resource_name.name}: {str(exc)}") from exc

    @classmethod
    def _read_resources(cls, configuration: YamlValidator, working_directory: Path) -> Dict[str, Resource]:
        resources: Dict[str, Resource] = {}
        for timeseries_resource in configuration.timeseries_resources:
            resources[timeseries_resource.name] = cls._read_resource(
                working_directory / timeseries_resource.name,
                timeseries_resource.typ,
                read_func=read_timeseries_resource,
            )

        for facility_resource_name in configuration.facility_resource_names:
            resources[facility_resource_name] = cls._read_resource(
                working_directory / facility_resource_name,
                read_func=read_facility_resource,
            )
        return resources

    def get_resources(self, configuration: YamlValidator) -> Dict[str, Resource]:
        return self._read_resources(configuration=configuration, working_directory=self._working_directory)


class FileConfigurationService(ConfigurationService):
    def __init__(self, configuration_path: Path):
        self._configuration_path = configuration_path

    def get_configuration(self) -> YamlValidator:
        with open(self._configuration_path) as configuration_file:
            main_resource = ResourceStream(
                name=self._configuration_path.stem,
                stream=configuration_file,
            )

            main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).get_validator(
                main_yaml=main_resource, enable_include=True, base_dir=self._configuration_path.parent
            )
            return main_yaml_model


class InvalidResourceException(Exception):
    pass


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
        self.configuration_service = configuration_service
        self.resource_service = resource_service

        self._resources = None
        self._dto = None
        self.__configuration = None

    @property
    def _configuration(self) -> YamlValidator:
        if self.__configuration is None:
            self.__configuration = self.configuration_service.get_configuration()

        return self.__configuration

    @property
    def resources(self):
        if self._resources is None:
            self._resources = self.resource_service.get_resources(self._configuration)

        return self._resources

    @property
    def dto(self) -> Asset:
        if self._dto is None:
            self._dto = map_yaml_to_dto(configuration=self._configuration, resources=self.resources)

        return self._dto

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
    def period(self):
        return Period(
            start=self._configuration.start,
            end=self._configuration.end,
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
                headers = resource.headers
                for header in headers:
                    token_references.append(f"{time_series.name};{header}")
            except InvalidResourceException:
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
