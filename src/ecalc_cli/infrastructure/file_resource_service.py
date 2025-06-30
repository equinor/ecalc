from pathlib import Path

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.file_context import FileContext, FileMark
from libecalc.presentation.yaml.resource_service import InvalidResource, ResourceService, TupleWithError
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class FileResourceService(ResourceService):
    def __init__(self, working_directory: Path, configuration: YamlValidator):
        self._working_directory = working_directory
        self._configuration = configuration

    def get_time_series_resources(self) -> TupleWithError[dict[str, TimeSeriesResource]]:
        resources: dict[str, TimeSeriesResource] = {}
        errors: list[InvalidResource] = []
        for timeseries_resource in self._configuration.timeseries_resources:
            try:
                resource_path = self._working_directory / timeseries_resource.name
                if not resource_path.is_file():
                    # Skip non-existing resources, that is handled in yaml validation
                    continue
                resource = MemoryResource.from_path(self._working_directory / timeseries_resource.name, allow_nans=True)
                resources[timeseries_resource.name] = TimeSeriesResource(resource).validate()
            except InvalidResourceException as e:
                if e.file_mark is not None:
                    start_file_mark = FileMark(
                        line_number=e.file_mark.row,
                        column=e.file_mark.column,
                    )
                else:
                    start_file_mark = None
                file_context = FileContext(
                    name=timeseries_resource.name,
                    start=start_file_mark,
                )

                errors.append(
                    InvalidResource(message=str(e), resource_name=timeseries_resource.name, file_context=file_context)
                )
        return resources, errors

    def get_facility_resources(self) -> TupleWithError[dict[str, Resource]]:
        resources: dict[str, Resource] = {}
        errors: list[InvalidResource] = []
        for facility_resource_name in self._configuration.facility_resource_names:
            try:
                resource_path = self._working_directory / facility_resource_name
                if not resource_path.is_file():
                    # Skip non-existing resources, that is handled in yaml validation
                    continue
                resource = MemoryResource.from_path(resource_path, allow_nans=False)
                resources[facility_resource_name] = resource
            except InvalidResourceException as e:
                if e.file_mark is not None:
                    start_file_mark = FileMark(
                        line_number=e.file_mark.row,
                        column=e.file_mark.column,
                    )
                else:
                    start_file_mark = None
                file_context = FileContext(
                    name=facility_resource_name,
                    start=start_file_mark,
                )
                errors.append(
                    InvalidResource(message=str(e), resource_name=facility_resource_name, file_context=file_context)
                )
        return resources, errors
