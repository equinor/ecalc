import logging
from collections.abc import Iterable
from datetime import datetime
from math import isnan
from typing import Self

import numpy as np
import pandas as pd

from libecalc.common.errors.exceptions import (
    InvalidColumnException,
    InvalidResourceException,
    NoColumnsException,
)
from libecalc.common.string.string_utils import get_duplicates
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

logger = logging.getLogger(__name__)


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


class TimeSeriesResource(Resource):
    """
    A time series resource containing time series.
    """

    def __init__(self, resource: Resource):
        self._resource = resource
        headers = resource.get_headers()

        if len(headers) == 0:
            raise InvalidResourceException("Invalid resource", "Resource must at least have one column")

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
                raise InvalidTimeSeriesResourceException(
                    "Time vector contains values that are not int or str, possibly caused by an extra comma."
                )
            self._time_vector = self._parse_time_vector(time_vector)
        except ValueError as e:
            # pandas.to_datetime might raise these two exceptions.
            # See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html
            raise InvalidTimeSeriesResourceException(f"Could not parse time vector: {str(e)}") from e

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
                    message=f"Column '{header}' does not match the length of the time vector.",
                )

            for index, value in enumerate(column):
                row = index + 1
                if not isinstance(value, float | int):
                    raise InvalidColumnException(
                        header=header,
                        row=row,
                        message=f"The timeseries column '{header}' contains non-numeric values in row {row}.",
                    )
                if isnan(value):
                    raise InvalidColumnException(
                        header=header,
                        row=row,
                        message=f"The timeseries column '{header}' contains empty values in row {row}.",
                    )

    @staticmethod
    def _parse_time_vector(date_input: list[int | str]) -> list[datetime]:
        """Parse entire timeseries in a single format.

        Args:
            date_input: Dates in unknown format.

        Returns:
            Consistent dates.

        Raises:
            ValueError:
                If dates do not match any of the given patterns.
                If dates are in an inconsistent format.
        """
        date_patterns = {
            # Only year supplied (YYYY e.g. 1996).
            "YEAR_ONLY": r"\d{4}",
            # ISO8601 date only e.g. '2024-01-31', '2024-12-01'.
            "ISO8601_date": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])",
            # ISO8601 date and time e.g. '2024-01-31 13:37:59', '2024-12-01 23:59:59'.
            "ISO8601_datetime": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])((\s|T)(\d{2}:){2}\d{2})",
            # European standard (day first) e.g. '31-01-2024', '1/12/2024', '01.12.2024'.
            "EU_date": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})",
            # European date with time, e.g. e.g. '31-01-2024 13:37:59', '1/12/2024 10:30:00', '01.01.2024 13:37')
            "EU_datetime": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})((\s|T)(\d{2}):(\d{2})(:\d{2})?)",
            # Explicitly not supported!
            "ILLEGAL_ISO8601_optional_time": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])((\s|T)(\d{2}:){2}\d{2})?",
            "ILLEGAL_EU_optional_time": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})((\s)(\d{2}):(\d{2})(:\d{2})?)?",
            # US standard date (month first), e.g. '12-31-2024', '9/1/2024'.
            "ILLEGAL_US_optional_time": r"(1[0-2]|0?[1-9])(\.|\/|-)(3[01]|[12][0-9]|0?[1-9])\2(\d{4})((\s|T)(\d{1,2})\:(\d{2})(:\d{2})?)?",
        }
        # Replace '/', '\' and '.', with '-' for consistency.
        check_dates: pd.Series = pd.Series(date_input).astype(str)
        date_list: list[str] = check_dates.str.replace(r"/|\.|\\", "-", regex=True).tolist()

        if check_dates.str.fullmatch(date_patterns["YEAR_ONLY"]).all():
            return pd.to_datetime(date_list, format="%Y", errors="raise").to_pydatetime().tolist()
        if check_dates.str.fullmatch(date_patterns["ISO8601_datetime"]).all():
            return pd.to_datetime(date_list, format="ISO8601", errors="raise").to_pydatetime().tolist()
        if check_dates.str.fullmatch(date_patterns["ISO8601_date"]).all():
            return pd.to_datetime(date_list, format="ISO8601", errors="raise").to_pydatetime().tolist()
        if check_dates.str.fullmatch(date_patterns["EU_datetime"]).all():
            return pd.to_datetime(date_list, dayfirst=True, errors="raise").to_pydatetime().tolist()
        if check_dates.str.fullmatch(date_patterns["EU_date"]).all():
            return pd.to_datetime(date_list, dayfirst=True, errors="raise").to_pydatetime().tolist()

        message = ""
        if (wrong_time_format := check_dates.str.match(r".*(am|pm|AM|PM)$")).any():
            message += "AM/PM are not supported in dates, only 24 hour clock is valid. "
            if not wrong_time_format.all():
                message += f" Found at approx lines: {np.flatnonzero(wrong_time_format) + 1}. "

        if (has_time := check_dates.str.fullmatch(r".*(\s(\d{2}:){2}\d{2})$")).any():
            if not (has_time.all() or not has_time.any()):
                most_with_time = has_time.value_counts().to_dict()
                locations = np.flatnonzero(~has_time) + 1 if most_with_time else np.flatnonzero(has_time) + 1
                message += (
                    f"Mostly dates {'with' if most_with_time else 'without'} time present, "
                    f"outliers found at approx lines: {locations}. "
                )
        eu = check_dates.str.fullmatch(rf"{date_patterns['ILLEGAL_EU_optional_time']}")
        us = check_dates.str.fullmatch(rf"{date_patterns['ILLEGAL_US_optional_time']}")
        if not (eu == us).all():
            # Only the dates that are definitively month first!
            only_us = us ^ (us & eu)
            us_locations = np.flatnonzero(only_us) + 1
            message += f"Month first (US style) dates are not supported, found at approx lines: {us_locations}. "

        year_only = check_dates.str.fullmatch(rf"{date_patterns['YEAR_ONLY']}")
        iso = check_dates.str.fullmatch(rf"{date_patterns['ILLEGAL_ISO8601_optional_time']}.*")
        unknown = ~(iso | eu | year_only)
        test_amounts = {
            "DAY-FIRST": eu.values.sum(),
            "ISO-8601": iso.values.sum(),
            "YEAR_ONLY": year_only.values.sum(),
            "UNKNOWN": unknown.values.sum(),
        }
        test = {"DAY-FIRST": eu, "ISO-8601": iso, "YEAR_ONLY": year_only, "UNKNOWN": unknown}
        most_prevalent_type = max(test_amounts, key=test_amounts.__getitem__)
        amount_most_prevalent = test_amounts.pop(most_prevalent_type)

        other_keys = [key for key, value in test_amounts.items() if value > 0]
        other_lines = ~test[most_prevalent_type]

        if other_lines.any():
            other_lines = np.flatnonzero(other_lines) + 1
            message += (
                f"Seems like you mostly have dates in {most_prevalent_type} format with"
                f" ~{round(amount_most_prevalent / len(check_dates) * 100)}% of the lines. "
            )
            if most_prevalent_type != "UNKNOWN":
                message += (
                    f"Found lines not conforming to this format at approx lines: {other_lines}. "
                    f"These lines have format(s) {other_keys}"
                )

        if message:
            err = ValueError(
                message + " Note: All line numbers exclude headers and comments, and may therefore be a bit off."
            )
            logger.info("Date parsing went wrong!", exc_info=err)
            raise err
        raise ValueError(
            "The provided dates doesn't match any of the accepted date formats, "
            "or contains inconsistently formatted dates."
        )

    def validate(self) -> Self:
        self._validate_time_vector()

        self._validate_columns()

        return self

    def get_time_vector(self) -> list[datetime]:
        return self._time_vector

    def get_headers(self) -> list[str]:
        return self._headers

    def get_column(self, header: str) -> list[float | int | str]:
        # TODO: Add validation on column so that we can remove 'str' from return type
        return self._resource.get_column(header)
