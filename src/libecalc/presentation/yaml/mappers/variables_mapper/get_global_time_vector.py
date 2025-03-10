from collections.abc import Iterable
from datetime import datetime, timedelta

import pandas as pd

import libecalc.common.time_utils
from libecalc.presentation.yaml.validation_errors import ValidationError


def _get_date_range(start: datetime, end: datetime, frequency: libecalc.common.time_utils.Frequency) -> set[datetime]:
    if frequency == libecalc.common.time_utils.Frequency.NONE:
        return set()

    date_range = pd.date_range(start=start, end=end, freq=frequency.value)
    return set(date_range.to_pydatetime())


def _get_end_boundary(frequency: libecalc.common.time_utils.Frequency, time_vector_set: set[datetime]) -> datetime:
    """If end boundary has not been specified explicitly, we attempt to make an educated guess for the
    user, based on output frequency provided and assuming data is forward filled.

    It is however recommended that the user specified END explicitly
    """
    time_vector: list[datetime] = sorted(time_vector_set)

    if frequency == libecalc.common.time_utils.Frequency.YEAR:
        return datetime(year=time_vector[-1].year + 1, month=1, day=1)
    elif frequency == libecalc.common.time_utils.Frequency.MONTH:
        return (time_vector[-1].replace(day=1) + timedelta(days=31)).replace(day=1)
    elif frequency == libecalc.common.time_utils.Frequency.DAY:
        return time_vector[-1] + timedelta(days=1)
    else:
        return max(
            time_vector
        )  # Frequency.NONE . We are clueless and user does not help us, just fallback to last time given


def get_global_time_vector(
    time_series_time_vector: Iterable[datetime],
    start: datetime | None = None,
    end: datetime | None = None,
    additional_dates: set[datetime] | None = None,
    frequency: libecalc.common.time_utils.Frequency = libecalc.common.time_utils.Frequency.NONE,
) -> list[datetime]:
    """

    Args:
        time_series_time_vector: all dates from time series that should influence time vector
        start: user specified start
        end: user specified end
        additional_dates: dates from the model configuration
        frequency: user specified frequency

    Returns: the actual set of dates that should be computed
    """
    time_vector: set[datetime] = set(time_series_time_vector)

    has_time_vector = len(time_vector) > 0
    has_start = start is not None
    has_end = end is not None
    has_frequency = frequency != libecalc.common.time_utils.Frequency.NONE
    if not (has_time_vector or (has_start and has_end) or (has_start and has_frequency)):
        raise ValidationError("No time series found, please provide one or specify a start and end (or frequency).")

    # Store start, end before adding dates from yaml. This is to make sure dates in yaml are trimmed.
    start = start or min(time_vector)

    # Add start
    time_vector.add(start)

    if not end:
        end = _get_end_boundary(frequency=frequency, time_vector_set=time_vector)

    # Add end
    time_vector.add(end)

    # Add all dates specified in yaml
    time_vector = time_vector.union(additional_dates or set())

    # Trim time vector based on start
    time_vector = {date for date in time_vector if date >= start}

    # Trim time vector based on end
    time_vector = {date for date in time_vector if date <= end}

    # Add all dates for frequency
    time_vector = time_vector.union(_get_date_range(start=start, end=end, frequency=frequency))

    return sorted(time_vector)
