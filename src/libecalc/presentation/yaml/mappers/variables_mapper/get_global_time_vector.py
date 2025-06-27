from collections.abc import Iterable
from datetime import datetime

import pandas as pd

import libecalc.common.time_utils
from libecalc.presentation.yaml.validation_errors import ValidationError


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
    start: datetime | None = None,
    end: datetime | None = None,
    additional_dates: set[datetime] | None = None,
) -> list[datetime]:
    """
    Generate a sorted list of unique datetime objects representing the global time vector,
    without adding frequency-based dates.

    Args:
        time_series_time_vector (Iterable[datetime]): The initial collection of datetime objects.
        start (datetime | None): Optional start boundary. If not provided, the earliest date in the time vector is used.
        end (datetime | None): Optional end boundary. If not provided, the latest date in the time vector is used.
        additional_dates (set[datetime] | None): Optional set of additional dates to include.

    Returns:
        list[datetime]: Sorted list of datetime objects within the specified boundaries.

    Raises:
        ValidationError: If neither a time vector nor both start and end are provided.
    """
    time_vector: set[datetime] = set(time_series_time_vector)

    has_time_vector = len(time_vector) > 0
    has_start = start is not None
    has_end = end is not None
    if not (has_time_vector or (has_start and has_end)):
        raise ValidationError("No time series found, please provide one or specify a start and end.")

    start = start or min(time_vector)
    time_vector.add(start)

    if not end:
        end = max(time_vector)

    time_vector.add(end)
    time_vector = time_vector.union(additional_dates or set())
    time_vector = {date for date in time_vector if date >= start}
    time_vector = {date for date in time_vector if date <= end}

    return sorted(time_vector)
