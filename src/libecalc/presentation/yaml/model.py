from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from libecalc.common.errors.exceptions import EcalcError, InvalidResourceHeaderException
from libecalc.common.logger import logger
from libecalc.common.time_utils import Frequency
from libecalc.dto import ResultOptions, VariablesMap
from libecalc.dto.component_graph import ComponentGraph
from libecalc.infrastructure.file_io import (
    read_facility_resource,
    read_timeseries_resource,
)
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto
from libecalc.presentation.yaml.yaml_entities import (
    Resource,
    ResourceStream,
)
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)


class YamlModel:
    def __init__(self, path: Path, output_frequency: Frequency) -> None:
        self._model_path = path
        self._output_frequency = output_frequency
        self._yaml_configuration = YamlModel._create_yaml_configuration(path)
        self.resources = YamlModel._read_resources(self._yaml_configuration, working_directory=path.parent)

        self._yaml_configuration.validate(self._get_validation_context(yaml_model=self._yaml_configuration))

        self.dto = map_yaml_to_dto(configuration=self._yaml_configuration, resources=self.resources, name=path.stem)

    def _find_resource_from_name(self, filename: str) -> Optional[Resource]:
        try:
            return next(resource for name, resource in self.resources.items() if name == filename)
        except StopIteration:
            return None

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
            YamlModelValidationContextNames.resource_file_names: [f"{resource}" for resource in self.resources],
            YamlModelValidationContextNames.expression_tokens: self._get_token_references(yaml_model=yaml_model),
            YamlModelValidationContextNames.model_types: self._get_model_types(yaml_model=yaml_model),
        }

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
            except ValueError:
                # Don't add any tokens if resource is invalid (unable to read header)
                continue

        for reference in yaml_model.variables:
            token_references.append(f"$var.{reference}")

        return token_references

    @property
    def start(self) -> datetime:
        return self._yaml_configuration.start

    @property
    def end(self) -> datetime:
        return self._yaml_configuration.end

    @property
    def variables(self) -> VariablesMap:
        return map_yaml_to_variables(
            configuration=self._yaml_configuration, resources=self.resources, result_options=self.result_options
        )

    @property
    def result_options(self) -> ResultOptions:
        return ResultOptions(
            start=self._yaml_configuration.start,
            end=self._yaml_configuration.end,
            output_frequency=self._output_frequency,
        )

    @property
    def graph(self) -> ComponentGraph:
        return self.dto.get_graph()

    @staticmethod
    def _create_yaml_configuration(main_yaml_path: Path) -> PyYamlYamlModel:
        with open(main_yaml_path) as model_file:
            main_resource = ResourceStream(
                name=main_yaml_path.name,
                stream=model_file,
            )

            main_yaml_model: PyYamlYamlModel = PyYamlYamlModel.read(
                main_yaml=main_resource, enable_include=True, base_dir=main_yaml_path.parent
            )
            return main_yaml_model

    @staticmethod
    def _read_resource(resource_name: Path, *args, read_func: Callable[..., Resource]):
        try:
            return read_func(resource_name, *args)
        except (InvalidResourceHeaderException, ValueError) as exc:
            logger.error(str(exc))
            raise EcalcError("Failed to read resource", f"Failed to read {resource_name.name}: {str(exc)}") from exc

    @staticmethod
    def _read_resources(yaml_configuration: PyYamlYamlModel, working_directory: Path) -> Dict[str, Resource]:
        resources: Dict[str, Resource] = {}
        for timeseries_resource in yaml_configuration.timeseries_resources:
            resources[timeseries_resource.name] = YamlModel._read_resource(
                working_directory / timeseries_resource.name,
                timeseries_resource.typ,
                read_func=read_timeseries_resource,
            )

        for facility_resource_name in yaml_configuration.facility_resource_names:
            resources[facility_resource_name] = YamlModel._read_resource(
                working_directory / facility_resource_name,
                read_func=read_facility_resource,
            )
        return resources
