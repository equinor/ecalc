import abc
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Protocol

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
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


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
        configuration = configuration_service.get_configuration()
        self.resources = resource_service.get_resources(configuration)
        self.dto = map_yaml_to_dto(configuration=configuration, resources=self.resources)
        self._configuration = configuration

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
