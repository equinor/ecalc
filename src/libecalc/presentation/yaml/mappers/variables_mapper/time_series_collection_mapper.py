import re
from datetime import datetime
from typing import Dict, List, Union

import pandas
from pydantic import Field, TypeAdapter, ValidationError
from typing_extensions import Annotated

from libecalc.common.errors.exceptions import InvalidResource
from libecalc.dto import TimeSeriesType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection import (
    DefaultTimeSeriesCollection,
    MiscellaneousTimeSeriesCollection,
)
from libecalc.presentation.yaml.resource import Resource, Resources
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    DumpFlowStyle,
)
from libecalc.presentation.yaml.yaml_entities import (
    YamlTimeseriesType,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

# Used here to make pydantic understand which object to instantiate.
TimeSeriesUnionType = Annotated[
    Union[MiscellaneousTimeSeriesCollection, DefaultTimeSeriesCollection],
    Field(discriminator="typ"),
]

time_series_type_map = {
    YamlTimeseriesType.MISCELLANEOUS.value: TimeSeriesType.MISCELLANEOUS,
    YamlTimeseriesType.DEFAULT.value: TimeSeriesType.DEFAULT,
}


def _parse_date(date_input: Union[int, str]) -> datetime:
    """
    Parse timeseries input:

    - Integer gets interpreted as year
    - Starting with YYYY.xx.xx, then we assume ISO 8601
    - Other than that, we assume a day-first format (e.g. Norwegian: DD.MM.YYYY)
    """
    # Columns with integers as dates are interpreted as year
    if isinstance(date_input, int):
        return datetime(date_input, 1, 1)

    date_split = re.split(r"\D+", date_input)
    if len(date_split[0]) == 4:
        return pandas.to_datetime(date_input).to_pydatetime()
    else:
        return pandas.to_datetime(date_input, dayfirst=True).to_pydatetime()


def parse_time_vector(time_vector: List[str]) -> List[datetime]:
    return [_parse_date(date_input) for date_input in time_vector]


def parse_time_series_from_resource(resource: Resource):
    time_series_resource_headers = resource.get_headers()

    if len(time_series_resource_headers) == 0:
        raise InvalidResource("Invalid resource", "Resource must at least have one column")

    if EcalcYamlKeywords.date in time_series_resource_headers:
        # Find the column named "DATE" and use that as time vector
        time_vector = resource.get_column(EcalcYamlKeywords.date)
        headers = [header for header in time_series_resource_headers if header != EcalcYamlKeywords.date]
    else:
        # Legacy: support random names for time vector as long as it is the first column
        time_vector = resource.get_column(time_series_resource_headers[0])
        headers = time_series_resource_headers[1:]

    return parse_time_vector(time_vector), headers


class TimeSeriesCollectionMapper:
    def __init__(self, resources: Resources):
        self.__resources = resources

    def from_yaml_to_dto(self, data: Dict) -> TimeSeriesUnionType:
        """
        Fixme: we do not use the input date format when reading Time Series Collections.
        """

        time_series = {
            "typ": data.get(EcalcYamlKeywords.type),
            "name": data.get(EcalcYamlKeywords.name),
            "influence_time_vector": data.get(EcalcYamlKeywords.time_series_influence_time_vector),
            "extrapolate_outside_defined_time_interval": data.get(
                EcalcYamlKeywords.time_series_extrapolate_outside_defined
            ),
            "interpolation_type": data.get(EcalcYamlKeywords.time_series_interpolation_type),
        }

        resource_name = data.get(EcalcYamlKeywords.file)
        time_series_resource = self.__resources.get(
            resource_name,
        )

        if time_series_resource is None:
            resource_name_context = "."
            if resource_name is not None:
                resource_name_context = f" with name '{resource_name}'"
            raise DataValidationError(
                data,
                message=f"Could not find resource{resource_name_context}",
                error_key=EcalcYamlKeywords.file,
                dump_flow_style=DumpFlowStyle.BLOCK,
            )

        try:
            time_vector, headers = parse_time_series_from_resource(time_series_resource)
        except InvalidResource as e:
            raise DataValidationError(
                data,
                message=str(e),
                error_key=EcalcYamlKeywords.file,
                dump_flow_style=DumpFlowStyle.BLOCK,
            ) from e

        columns = []

        for header in headers:
            try:
                columns.append(time_series_resource.get_column(header))
            except InvalidResource:
                # Validation handled below when creating TimeSeries class
                pass

        time_series["headers"] = headers
        time_series["time_vector"] = time_vector
        time_series["columns"] = columns

        try:
            return TypeAdapter(TimeSeriesUnionType).validate_python(time_series)
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e, dump_flow_style=DumpFlowStyle.BLOCK) from e
