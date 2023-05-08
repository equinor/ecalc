from datetime import datetime
from math import isnan
from typing import List, Literal, Optional, Tuple, Union

from libecalc.common.logger import logger
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import InterpolationType, TimeSeriesType
from libecalc.input.mappers.variables_mapper.time_series import TimeSeries
from pydantic import Field, root_validator, validator


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
    name: str = Field(regex=r"^[A-Za-z][A-Za-z0-9_]*$")

    headers: List[str] = Field(
        regex=r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:\/]*$", default_factory=list
    )  # Does not include date header
    columns: List[List[float]] = Field(default_factory=list)
    time_vector: List[datetime] = Field(default_factory=list)

    influence_time_vector: Optional[bool] = True
    extrapolate_outside_defined_time_interval: Optional[bool] = None
    interpolation_type: InterpolationType = None

    class Config:
        allow_mutation = False
        validate_all = True

    @validator("influence_time_vector")
    def set_influence_time_vector_default(cls, value):
        return value if value is not None else True

    @validator("extrapolate_outside_defined_time_interval")
    def set_extrapolate_outside_defined_time_interval_default(cls, value):
        return value if value is not None else False

    @validator("time_vector")
    def check_that_dates_are_ok(cls, dates):
        if len(dates) == 0:
            raise ValueError("Time vectors must have at least one record")
        if not (len(dates) == len(set(dates))):
            raise ValueError("The list of dates have duplicates. Duplicated dates are currently not supported.")
        return dates

    @root_validator()
    def check_that_lists_match(cls, values):
        headers = values.get("headers")
        columns = values.get("columns")
        time_vector = values.get("time_vector")

        if time_vector is None or columns is None:
            logger.debug(
                "Time vector or column is not initialized. This case should not be handled here, "
                "it probably means a previous validation failed."
            )
            return values

        time_vector_length = len(time_vector)
        headers_length = len(headers)

        if headers_length == 0:
            raise ValueError("Headers must at least have one column")

        number_of_columns = len(values.get("columns"))

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
        values["time_vector"] = sorted_time_vector
        values["columns"] = sorted_columns
        return values

    @validator("columns")
    def check_that_columns_are_ok(cls, columns, values):
        headers = values.get("headers")

        if headers is None or columns is None:
            return columns

        for column, header in zip(columns, headers):
            for value in column:
                if isnan(value):
                    reference_id = f'{values["name"]};{header}'
                    raise ValueError(
                        f"The timeseries column '{reference_id}' contains empty values. "
                        f"Please check your file for missing data, each column should define values for all timesteps.",
                    )

        return columns

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
    typ: Literal[TimeSeriesType.MISCELLANEOUS] = TimeSeriesType.MISCELLANEOUS

    @validator("interpolation_type", pre=True, always=True)
    def interpolation_is_required(cls, value):
        if value is None:
            raise ValueError("interpolation_type must be specified for the MISCELLANEOUS time series type.")
        return value


class DefaultTimeSeriesCollection(TimeSeriesCollection):
    typ: Literal[TimeSeriesType.DEFAULT] = TimeSeriesType.DEFAULT

    @validator("extrapolate_outside_defined_time_interval", pre=True, always=True)
    def extrapolate_outside_defined_time_interval_cannot_be_set(cls, value):
        if value is not None:
            raise ValueError(
                "extrapolate_outside_defined_time_interval cannot be set on "
                "DEFAULT-type (since DEFAULT-models should not be possible to extrapolate)."
            )

        return value

    @validator("interpolation_type", pre=True, always=True)
    def set_default_interpolation_type(cls, value):
        if value is not None:
            raise ValueError(
                "interpolation_type cannot be set on DEFAULT-type "
                "(since DEFAULT-models can only have RIGHT interpolation)."
            )
        return InterpolationType.RIGHT
