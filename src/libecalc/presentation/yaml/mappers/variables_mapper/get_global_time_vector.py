from collections.abc import Iterable
from datetime import datetime

import pandas as pd

import libecalc.common.time_utils
from libecalc.domain.component_validation_error import DomainValidationException


class InvalidEndDate(DomainValidationException):
    pass


def _get_date_range(start: datetime, end: datetime, frequency: libecalc.common.time_utils.Frequency) -> set[datetime]:
    """
    Generate a set of datetime objects between start and end at the specified frequency.

    Args:
        start (datetime): The start datetime of the range (inclusive).
        end (datetime): The end datetime of the range (inclusive).
        frequency (libecalc.common.time_utils.Frequency): The frequency at which to generate dates.
            If Frequency.NONE, returns an empty set.

    Returns:
        set[datetime]: Set of datetime objects at the specified frequency between start and end.
    """
    if frequency == libecalc.common.time_utils.Frequency.NONE:
        return set()

    date_range = pd.date_range(start=start, end=end, freq=frequency.value)
    return set(date_range.to_pydatetime())


def get_global_time_vector(
    time_series_time_vector: Iterable[datetime],
    end: datetime,
    start: datetime | None = None,
    additional_dates: set[datetime] | None = None,
) -> list[datetime]:
    """
    Generate a sorted list of unique datetime objects representing the global time vector,
    without adding frequency-based dates.

    Args:
        time_series_time_vector (Iterable[datetime]): The initial collection of datetime objects.
        end (datetime): End boundary for the time vector.
        start (datetime | None): Optional start boundary. If not provided, the earliest date in the time vector is used.
        additional_dates (set[datetime] | None): Optional set of additional dates to include.

    Returns:
        list[datetime]: Sorted list of datetime objects within the specified boundaries.

    Raises:
        DomainValidationException: If the time vector can not be constructed due to missing dates or invalid boundaries.
    """
    time_vector = set(time_series_time_vector)
    if not time_vector and not start:
        raise DomainValidationException(
            "No time series found, please provide one or specify both a start date and an end date."
        )
    start = start or min(time_vector)
    if end <= start:
        raise InvalidEndDate("The end date given in the YAML file must come after the start date.")
    time_vector.update({start, end})
    if additional_dates:
        time_vector.update(additional_dates)
    return sorted(date for date in time_vector if start <= date <= end)
