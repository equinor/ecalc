import re
from datetime import datetime
from typing import Dict, List, Tuple, Union

import pandas
from pydantic import Field, TypeAdapter, ValidationError
from typing_extensions import Annotated

from libecalc.dto import TimeSeriesType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection import (
    DefaultTimeSeriesCollection,
    MiscellaneousTimeSeriesCollection,
)
from libecalc.presentation.yaml.validation_errors import (
    DtoValidationError,
    DumpFlowStyle,
)
from libecalc.presentation.yaml.yaml_entities import (
    Resource,
    Resources,
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


def _setup_time_series_data(
    date_index: int,
    time_series_resource: Resource,
) -> Tuple[List[Union[datetime, pandas.Timestamp]], List[List]]:
    time_vector = [_parse_date(date_input) for date_input in time_series_resource.data[date_index]]
    columns = time_series_resource.data[:date_index] + time_series_resource.data[date_index + 1 :]

    return time_vector, columns


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

        time_series_resource = self.__resources.get(
            data.get(EcalcYamlKeywords.file),
            Resource(headers=[], data=[]),
        )

        if EcalcYamlKeywords.date in time_series_resource.headers:
            # Find the column named "DATE" and use that as time vector
            date_index = time_series_resource.headers.index(EcalcYamlKeywords.date)
            headers = [header for header in time_series_resource.headers if header != EcalcYamlKeywords.date]
            time_vector, columns = _setup_time_series_data(
                date_index=date_index, time_series_resource=time_series_resource
            )
        else:
            # Legacy: support random names for time vector as long as it is the first column
            time_vector, columns = _setup_time_series_data(date_index=0, time_series_resource=time_series_resource)
            headers = time_series_resource.headers[1:]  # Remove date header

        time_series["headers"] = headers
        time_series["time_vector"] = time_vector
        time_series["columns"] = columns

        try:
            return TypeAdapter(TimeSeriesUnionType).validate_python(time_series)
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e, dump_flow_style=DumpFlowStyle.BLOCK) from e
