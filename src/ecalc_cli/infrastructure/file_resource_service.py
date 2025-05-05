from collections.abc import Callable
from pathlib import Path

from libecalc.common.errors.exceptions import EcalcError, InvalidHeaderException, InvalidResourceException
from libecalc.common.logger import logger
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.yaml_entities import MemoryResource, YamlTimeseriesType
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class FileResourceService(ResourceService):
    def __init__(self, working_directory: Path):
        self._working_directory = working_directory

    @staticmethod
    def _read_resource(resource_name: Path, *args, read_func: Callable[..., MemoryResource]) -> MemoryResource:
        try:
            return read_func(resource_name, *args)
        except (InvalidHeaderException, ValueError) as exc:
            logger.error(str(exc))
            raise EcalcError("Failed to read resource", f"Failed to read {resource_name.name}: {str(exc)}") from exc

    @classmethod
    def _read_resources(cls, configuration: YamlValidator, working_directory: Path) -> dict[str, MemoryResource]:
        resources: dict[str, MemoryResource | TimeSeriesResource] = {}
        for timeseries_resource in configuration.timeseries_resources:
            if timeseries_resource.typ not in (YamlTimeseriesType.DEFAULT, YamlTimeseriesType.MISCELLANEOUS):
                raise InvalidResourceException(
                    title="Invalid time series type",
                    message=f"Invalid type '{timeseries_resource.typ}' for resource '{timeseries_resource.name}'.",
                )

            resources[timeseries_resource.name] = TimeSeriesResource(
                cls._read_resource(
                    working_directory / timeseries_resource.name,
                    False,
                    read_func=MemoryResource.from_path,
                )
            )

        for facility_resource_name in configuration.facility_resource_names:
            resources[facility_resource_name] = cls._read_resource(
                working_directory / facility_resource_name, True, read_func=MemoryResource.from_path
            )
        return resources

    def get_resources(self, configuration: YamlValidator) -> dict[str, Resource]:
        return self._read_resources(configuration=configuration, working_directory=self._working_directory)
