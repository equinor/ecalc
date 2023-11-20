from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

import pandas as pd
from scipy.interpolate import interp1d

import libecalc.common.time_utils
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series import TimeSeries
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection import (
    TimeSeriesCollection,
)
from libecalc.presentation.yaml.validation_errors import ValidationError


def _split_time_vector(
    time_vector: List[datetime],
    start: datetime,
    end: datetime,
) -> Tuple[int, List[datetime], int]:
    """Find the entries between start and end, also counting the number of entries before start and after end."""
    number_of_entries_before = len([date for date in time_vector if date < start])
    number_of_entries_after = len([date for date in time_vector if date > end])
    entries_between = [date for date in time_vector if start <= date <= end]
    return number_of_entries_before, entries_between, number_of_entries_after


def _get_interpolation_kind(rate_interpolation_type: InterpolationType) -> str:
    if rate_interpolation_type == InterpolationType.LINEAR:
        return "linear"
    elif rate_interpolation_type == InterpolationType.RIGHT:
        return "previous"
    elif rate_interpolation_type == InterpolationType.LEFT:
        return "next"
    else:
        raise ValueError(f"Invalid interpolation typem, got {rate_interpolation_type}.")


def _interpolate(
    time_series: TimeSeries, time_vector: List[datetime], rate_interpolation_type: InterpolationType
) -> List[float]:
    interpolation_kind = _get_interpolation_kind(
        rate_interpolation_type=rate_interpolation_type,
    )

    start_time = time_series.time_vector[0]

    if len(time_series.time_vector) == 1:
        # add dummy time 1 second later
        setup_times = [0, 1]
        setup_y = 2 * time_series.series
    else:
        # Interpolator x variable is number of seconds from first date time
        setup_times = [(time - start_time).total_seconds() for time in time_series.time_vector]
        setup_y = time_series.series

    interpolator = interp1d(x=setup_times, y=setup_y, kind=interpolation_kind)
    target_times = [(time - start_time).total_seconds() for time in time_vector]
    return list(interpolator(target_times))


def fit_time_series_to_time_vector(
    time_series: TimeSeries,
    time_vector: List[datetime],
    extrapolate_outside_defined_time_interval: bool,
    interpolation_type: InterpolationType,
) -> List[float]:
    start, end = time_series.time_vector[0], time_series.time_vector[-1]
    number_of_entries_before, entries_between, number_of_entries_after = _split_time_vector(
        time_vector, start=start, end=end
    )

    if extrapolate_outside_defined_time_interval:
        extrapolation_after_value = time_series.series[-1]
    else:
        extrapolation_after_value = 0.0

    before_values = [0.0] * number_of_entries_before
    between_values = _interpolate(
        time_series=time_series, time_vector=entries_between, rate_interpolation_type=interpolation_type
    )
    after_values = [extrapolation_after_value] * number_of_entries_after

    return [*before_values, *between_values, *after_values]


def _get_date_range(start: datetime, end: datetime, frequency: libecalc.common.time_utils.Frequency) -> Set[datetime]:
    if frequency == libecalc.common.time_utils.Frequency.NONE:
        return set()

    date_range = pd.date_range(start=start, end=end, freq=frequency.value)
    return set(date_range.to_pydatetime())


def _get_end_boundary(frequency: libecalc.common.time_utils.Frequency, time_vector_set: Set[datetime]) -> datetime:
    """If end boundary has not been specified explicitly, we attempt to make an educated guess for the
    user, based on output frequency provided and assuming data is forward filled.

    It is however recommended that the user specified END explicitly
    """
    time_vector: List[datetime] = sorted(time_vector_set)

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
    time_series_collections: List[TimeSeriesCollection],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    additional_dates: Optional[Set[datetime]] = None,
    frequency: libecalc.common.time_utils.Frequency = libecalc.common.time_utils.Frequency.NONE,
) -> List[datetime]:
    time_vector: Set[datetime] = set()

    # Add all dates from time series that should influence time vector
    for time_series_collection in time_series_collections:
        if time_series_collection.influence_time_vector:
            time_vector = time_vector.union(time_series_collection.time_vector)

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
