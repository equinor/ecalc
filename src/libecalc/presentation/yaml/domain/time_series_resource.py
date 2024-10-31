import re
from collections.abc import Iterable
from datetime import datetime
from math import isnan
from typing import Self, Union

from pandas.errors import ParserError

from libecalc.common.errors.exceptions import (
    InvalidColumnException,
    InvalidHeaderException,
    InvalidResourceException,
    NoColumnsException,
)
from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection_mapper import parse_time_vector
from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


class InvalidTimeSeriesResourceException(InvalidResourceException):
    def __init__(self, message):
        super().__init__("Invalid time series resource", message)


class EmptyTimeVectorException(InvalidTimeSeriesResourceException):
    def __init__(self):
        super().__init__("The time vector is empty")


class DuplicateDatesException(InvalidTimeSeriesResourceException):
    def __init__(self, duplicates: Iterable[datetime]):
        self.duplicates = duplicates
        super().__init__(f"The time series resource contains duplicate dates: {','.join(map(str, duplicates))}")


def _is_header_valid(header: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:\/]*$", header))


class TimeSeriesResource(Resource):
    """
    A time series resource containing time series
    """

    def __init__(self, resource: Resource):
        self._resource = resource
        headers = resource.get_headers()

        if len(headers) == 0:
            raise InvalidResourceException("Invalid resource", "Resource must at least have one column")

        for header in headers:
            if not _is_header_valid(header):
                raise InvalidHeaderException(
                    "The time series resource header contains illegal characters. "
                    "Allowed characters are: ^[A-Za-z][A-Za-z0-9_.,\\-\\s#+:\\/]*$"
                )

        if EcalcYamlKeywords.date in headers:
            # Find the column named "DATE" and use that as time vector
            time_vector = resource.get_column(EcalcYamlKeywords.date)
            headers = [header for header in headers if header != EcalcYamlKeywords.date]
        else:
            # Legacy: support random names for time vector as long as it is the first column
            time_vector = resource.get_column(headers[0])
            headers = headers[1:]

        try:
            if not all(isinstance(time, int | str) for time in time_vector):
                # time_vector may be a list of floats for example.
                # This might happen if the resource contains an extra comma only in a single row.
                raise InvalidTimeSeriesResourceException("could not parse time vector.")
            self._time_vector = parse_time_vector(time_vector)
        except (ParserError, ValueError) as e:
            # pandas.to_datetime might raise these two exceptions.
            # See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html
            raise InvalidTimeSeriesResourceException("could not parse time vector.") from e

        self._headers = headers

    def _validate_time_vector(self) -> None:
        if len(self._time_vector) == 0:
            raise EmptyTimeVectorException()
        duplicates = get_duplicates(self._time_vector)
        if len(duplicates) != 0:
            raise DuplicateDatesException(duplicates=duplicates)

    def _validate_columns(self):
        headers = self.get_headers()
        columns = [self.get_column(header) for header in headers]
        time_vector = self.get_time_vector()

        time_vector_length = len(time_vector)
        headers_length = len(headers)

        if headers_length == 0:
            raise NoColumnsException()

        number_of_rows = len(columns[0])

        if number_of_rows == 0:
            raise InvalidResourceException("No rows in resource", "The resource should have at least one row.")

        if not (number_of_rows == time_vector_length):
            raise InvalidResourceException(
                "Rows mismatch",
                f"The number of records for times and data do not match: data: {number_of_rows}, time_vector: {time_vector_length}",
            )

        for column, header in zip(columns, headers):
            if len(column) != time_vector_length:
                raise InvalidColumnException(
                    header=header,
                    message="Column '{header}' does not match the length of the time vector.",
                )

            for index, value in enumerate(column):
                row = index + 1
                if not isinstance(value, float | int):
                    raise InvalidColumnException(
                        header=header,
                        row=row,
                        message="The timeseries column '{header}' contains non-numeric values in row {row}.",
                    )
                if isnan(value):
                    raise InvalidColumnException(
                        header=header,
                        row=row,
                        message="The timeseries column '{header}' contains empty values in row {row}.",
                    )

    def validate(self) -> Self:
        self._validate_time_vector()

        self._validate_columns()

        return self

    def get_time_vector(self) -> list[datetime]:
        return self._time_vector

    def get_headers(self) -> list[str]:
        return self._headers

    def get_column(self, header: str) -> list[Union[float, int, str]]:
        # TODO: Add validation on column so that we can remove 'str' from return type
        return self._resource.get_column(header)
