from datetime import datetime
from math import isnan
from typing import List, Literal, Optional, Tuple, Union

from pydantic import ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import InterpolationType, TimeSeriesType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series import TimeSeries


def transpose(data: List[List]) -> List[List]:
    return list(map(list, zip(*data)))


def _sort_time_series_data(
    time_vector: List[Union[datetime]],
    columns: List[List],
) -> Tuple[List[Union[datetime]], List[List]]:
    timeseries_columns = [time_vector, *columns]
    timeseries_rows = transpose(timeseries_columns)
    sorted_timeseries_rows = sorted(timeseries_rows, key=lambda row: row[0])
    sorted_timeseries_columns = transpose(sorted_timeseries_rows)
    return sorted_timeseries_columns[0], sorted_timeseries_columns[1:]


class TimeSeriesCollection(EcalcBaseModel):
    typ: TimeSeriesType
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")

    headers: List[Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:\/]*$")]] = Field(
        default_factory=list
    )  # Does not include date header
    columns: List[List[float]] = Field(default_factory=list)
    time_vector: List[datetime] = Field(default_factory=list)

    influence_time_vector: Optional[bool] = True
    extrapolate_outside_defined_time_interval: Optional[bool] = None
    interpolation_type: InterpolationType = None
    model_config = ConfigDict(validate_default=True)

    @field_validator("influence_time_vector")
    @classmethod
    def set_influence_time_vector_default(cls, value):
        return value if value is not None else True

    @field_validator("extrapolate_outside_defined_time_interval")
    @classmethod
    def set_extrapolate_outside_defined_time_interval_default(cls, value):
        return value if value is not None else False

    @field_validator("time_vector")
    @classmethod
    def check_that_dates_are_ok(cls, dates):
        if len(dates) == 0:
            raise ValueError("Time vectors must have at least one record")
        if not (len(dates) == len(set(dates))):
            raise ValueError("The list of dates have duplicates. Duplicated dates are currently not supported.")
        return dates

    @model_validator(mode="after")
    def check_that_lists_match(self):
        headers = self.headers
        columns = self.columns
        time_vector = self.time_vector

        time_vector_length = len(time_vector)
        headers_length = len(headers)

        if headers_length == 0:
            raise ValueError("Headers must at least have one column")

        number_of_columns = len(columns)

        if number_of_columns == 0:
            raise ValueError("Data vector must at least have one column")

        if not (headers_length == number_of_columns):
            raise ValueError(
                f"The number of columns provided do not match for header and data: data: {number_of_columns}, headers: {headers_length}"
            )

        number_of_rows = len(columns[0])

        if number_of_rows == 0:
            raise ValueError("Data must have at least one record")

        if not (number_of_rows == time_vector_length):
            raise ValueError(
                f"The number of records for times and data do not match: data: {number_of_rows}, time_vector: {time_vector_length}"
            )

        sorted_time_vector, sorted_columns = _sort_time_series_data(time_vector, columns)
        self.time_vector = sorted_time_vector
        self.columns = sorted_columns
        return self

    @model_validator(mode="after")
    def check_that_columns_are_ok(self):
        headers = self.headers

        if headers is None or self.columns is None:
            return self.columns

        for column, header in zip(self.columns, headers):
            for value in column:
                if isnan(value):
                    reference_id = f"{self.name};{header}"
                    raise ValueError(
                        f"The timeseries column '{reference_id}' contains empty values. "
                        f"Please check your file for missing data, each column should define values for all timesteps.",
                    )

        return self

    @property
    def time_series(self):
        return [
            TimeSeries(
                reference_id=f"{self.name};{header}",
                time_vector=self.time_vector,
                series=column,
            )
            for header, column in zip(self.headers, self.columns)
        ]


class MiscellaneousTimeSeriesCollection(TimeSeriesCollection):
    typ: Literal[TimeSeriesType.MISCELLANEOUS] = TimeSeriesType.MISCELLANEOUS.value

    @field_validator("interpolation_type", mode="before")
    @classmethod
    def interpolation_is_required(cls, value):
        if value is None:
            raise ValueError("interpolation_type must be specified for the MISCELLANEOUS time series type.")
        return value


class DefaultTimeSeriesCollection(TimeSeriesCollection):
    typ: Literal[TimeSeriesType.DEFAULT] = TimeSeriesType.DEFAULT.value

    @field_validator("extrapolate_outside_defined_time_interval", mode="before")
    @classmethod
    def extrapolate_outside_defined_time_interval_cannot_be_set(cls, value):
        if value is not None:
            raise ValueError(
                "extrapolate_outside_defined_time_interval cannot be set on "
                "DEFAULT-type (since DEFAULT-models should not be possible to extrapolate)."
            )

        return value

    @field_validator("interpolation_type", mode="before")
    def set_default_interpolation_type(cls, value):
        if value is not None:
            raise ValueError(
                "interpolation_type cannot be set on DEFAULT-type "
                "(since DEFAULT-models can only have RIGHT interpolation)."
            )
        return InterpolationType.RIGHT
