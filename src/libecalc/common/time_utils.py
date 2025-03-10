from __future__ import annotations

import enum
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Self

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from libecalc.common.errors.exceptions import (
    InvalidDateException,
    ProgrammingError,
)
from libecalc.common.units import UnitConstants


def calculate_delta_days(time_vector: ArrayLike) -> NDArray[np.float64]:
    return np.array([x.total_seconds() / UnitConstants.SECONDS_IN_A_DAY for x in np.diff(time_vector)])


@dataclass(eq=True, frozen=True, order=True)
class Period:
    """A period of time, defined by a start and end date."""

    start: datetime = datetime.min
    end: datetime = datetime.max.replace(microsecond=0)

    def __str__(self) -> str:
        return f"{self.start};{self.end}"  #  need something other than : to be able to split a string into two dates

    def __contains__(self, date_or_period: datetime | Period) -> bool:
        """
        A period of time is defined as [start, end>, ie inclusive start and exclusive end.

        Check if a date or another period is contained within this period.

        Args:
            date_or_period: A date or period of interest

        Returns:
            Whether the given date or period is contained within this period
        """
        if isinstance(date_or_period, datetime):
            return self.start <= date_or_period < self.end
        if isinstance(date_or_period, Period):
            return self.start <= date_or_period.start < date_or_period.end <= self.end

    @staticmethod
    def intersects(first: Period, second: Period) -> bool:
        """Decide if two periods intersects.

        Args:
            first: A period
            second: Another period

        Returns:
            Whether the two periods intersects
        """
        return first.start in second or second.start in first

    @staticmethod
    def intersection(first: Period, second: Period) -> Period | None:
        """Find the intersection between two periods.

        Args:
            first: A period
            second: Another period

        Returns:
            The intersection between the two periods. Returns None if the periods do not intersect.
        """
        if not Period.intersects(first, second):
            return None

        return Period(max(first.start, second.start), min(first.end, second.end))

    def get_period_indices(self, periods: Periods) -> tuple[int, int]:
        """Given a list of periods, find the indices of the start and end of this objects period in the list.

           The start and end dates of this object's period must be within the start and end dates within
           the given list of periods.
        Args:
            periods: A Periods object, containing a list of Periods

        Returns:

        """
        try:
            start_index = periods.start_dates.index(max(self.start, periods.periods[0].start))
            end_index = periods.all_dates.index(min(self.end, periods.periods[-1].end))

            return start_index, end_index
        except (IndexError, ValueError) as e:
            raise ProgrammingError(
                "Trying to access a period index that does not exist. Please contact eCalc support.\n\t"
                f"Period: {self.start}:{self.end} - periods: {periods}"
            ) from e

    def get_timesteps(self, timesteps: list[datetime]) -> list[datetime]:
        """
        Get all given timesteps that are within this period.
        Returns empty list if all timesteps are outside period.
        """
        timesteps = [timestep for timestep in timesteps if self.__contains__(timestep)]

        return timesteps

    def get_periods(self, periods: Periods) -> Periods:
        """Given a list of periods, find those that are within this object's period.
        Args:
            periods: A Periods object, containing a list of Periods

        Returns:

        """
        if Period.intersects(periods.period, self):
            start_index, end_index = self.get_period_indices(periods)
            return periods[start_index:end_index]
        else:
            return Periods([])

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


@dataclass(eq=True, frozen=True, order=True)
class Periods:
    periods: list[Period]

    @staticmethod
    def create_periods(times: list[datetime], include_before: bool = True, include_after: bool = True) -> Periods:
        """
        Create periods from the provided datetimes
        :param times: the sorted times to create periods from
        :param include_before: whether to add a period that ends with the first provided datetime, i.e. define a period
        before the earliest provided datetime.
        :param include_after: whether to add a period that starts with the last provided datetime, i.e. define a period
        after the latest provided datetime.
        :return:
        """
        if len(times) == 0:
            return Periods([])

        periods = []

        if include_before:
            periods.append(
                Period(
                    end=times[0],
                )
            )

        periods.extend([Period(start=times[index], end=times[index + 1]) for index in range(len(times) - 1)])

        if include_after:
            periods.append(Period(start=times[-1]))

        return Periods(periods=periods)

    def __iter__(self) -> Iterator[Period]:
        return self.periods.__iter__()

    def get_period(self, period: Period) -> Period | None:
        for _period in self.periods:
            if period in _period:
                return _period

        return None

    @property
    def all_dates(self) -> list[datetime]:
        return self.start_dates + [self.end_dates[-1]]

    @property
    def start_dates(self) -> list[datetime]:
        return [period.start for period in self.periods]

    @property
    def end_dates(self) -> list[datetime]:
        return [period.end for period in self.periods]

    @property
    def last_date(self) -> datetime:
        return self.end_dates[-1]

    @property
    def first_date(self) -> datetime:
        return self.start_dates[0]

    def __add__(self, other):
        return Periods(self.periods + other.periods)

    def __len__(self):
        return len(self.periods)

    def __getitem__(self, indices: slice | int | list[int]) -> Self:
        if isinstance(indices, slice):
            return Periods(self.periods[indices])
        elif isinstance(indices, int):
            return Periods([self.periods[indices]])
        elif isinstance(indices, list):
            return Periods([self.periods[i] for i in indices])
        raise ValueError(
            f"Unsupported indexing operation. Got '{type(indices)}', expected indices as a slice, single index or a list of indices"
        )

    @property
    def period(self):
        return Period(self.periods[0].start, self.periods[-1].end)


def define_time_model_for_period(time_model_data: Any | None, target_period: Period) -> dict[Period, Any] | None:
    """Process time model based on the target period.

    Steps:
        - Add a default start date if the model is not already a time model
        - Filter definitions outside given time period
        - Adjust start date of the first model to the period

    Args:
        time_model_data: A model that can vary based on time, e.g., {1900-01-01: some model, 1950-01-01: some other model}
        target_period: Period for which a model is defined (START, END specified by user or default to everything)

    Returns:
        The time model for the target period
    """
    if time_model_data is None:
        return None

    # Make sure the model is a time model
    time_model_data = default_temporal_model(time_model_data, default_period=target_period)

    dict_to_return = {}
    for model_period, model in time_model_data.items():
        if Period.intersects(model_period, target_period):
            dict_to_return[Period.intersection(model_period, target_period)] = model

    return dict_to_return


class Frequency(str, enum.Enum):
    """Represents frequency/resolution of output data
    Using the offset aliases from pandas
    YS: year start
    MS: month start
    D: calendar day.
    """

    NONE = None
    YEAR = "YS"
    MONTH = "MS"
    DAY = "D"

    def formatstring(self) -> str:
        """The format to write a string describing a certain period of time."""
        if self.value == "YS":
            return "%Y"
        elif self.value == "MS":
            return "%m/%Y"
        else:
            return "%d/%m/%Y"


def resample_periods(
    periods: Periods,
    frequency: Frequency,
    include_start_date: bool = True,
    include_end_date: bool = True,
) -> Periods:
    """Makes a list of periods, based on the first and last date in the original periods and the frequency

    Args:
        periods: The original list of periods
        frequency: The reporting frequency
        include_start_date: Whether to include the start date if it is not part of the requested reporting frequency
        include_end_date: Whether to include the end date if it is not part of the requested reporting frequency

    Returns:list of periods dates according to given input

    """
    if frequency is not Frequency.NONE:
        periods = Periods.create_periods(
            times=create_start_and_end_dates_for_periods(
                start=periods.periods[0].start,
                end=periods.periods[-1].end,
                frequency=frequency,
                include_start_date=include_start_date,
                include_end_date=include_end_date,
            ),
            include_before=False,
            include_after=False,
        )
    else:
        periods = periods
    return periods


def create_start_and_end_dates_for_periods(
    frequency: Frequency, start: datetime, end: datetime, include_start_date: bool, include_end_date: bool
) -> list[datetime]:
    """

    Args:
        frequency: The requested frequency
        start: The start date
        end: The end date
        include_start_date: Whether to include the start date if it is not part of the requested frequency
        include_end_date:  Whether to include the end date if it is not part of the requested frequency

    Returns:
        A list of dates (and possibly including the start/end dates) between the given start and end dates following
        the requested frequency

    """
    # If the start date or end date is part of the date_range made by the frequency, the returned date range will
    # always include the start and end date (no matter what the include_start_date and include_end_date booleans are).
    # To avoid this add one day to start and subtract one day from end.
    date_range = pd.date_range(start=start + timedelta(days=1), end=end - timedelta(days=1), freq=frequency.value)

    time_steps = [clear_time(time_step) for time_step in date_range]
    if include_start_date:
        time_steps = [clear_time(start)] + time_steps
    if include_end_date:
        time_steps = [clear_time(end)] + time_steps

    return sorted(set(time_steps))


def clear_time(d: datetime) -> datetime:
    return datetime.combine(d.date(), datetime.min.time())


def is_temporal_model(data: dict) -> bool:
    """Check if the data is a time dependent dict. A time dependent dict is a dict where the keys are dates or periods."""
    if isinstance(data, dict):
        is_period = []
        is_date = []
        is_not_period_keys = []
        for key in data:
            if isinstance(key, date):
                is_date.append(True)
                is_period.append(False)
            elif isinstance(key, Period):
                is_period.append(True)
                is_date.append(False)
            else:
                try:
                    split_key = key.split(";")
                    if len(split_key) == 1:
                        datetime.strptime(split_key[0], "%Y-%m-%dT%H:%M:%S")
                        is_date.append(True)
                        is_period.append(False)
                    else:
                        datetime.strptime(split_key[0], "%Y-%m-%d %H:%M:%S")
                        datetime.strptime(split_key[1], "%Y-%m-%d %H:%M:%S")
                        is_period.append(True)
                        is_date.append(False)
                except (TypeError, ValueError):
                    is_not_period_keys.append(str(key))
                    is_period.append(False)
                    is_date.append(False)
        if any(is_date):
            if not all(is_date):
                raise InvalidDateException(
                    title="Invalid model",
                    message="Temporal models should only contain date keys. "
                    f"Invalid date(s): {','.join(is_not_period_keys)}",
                )
            return True
        if any(is_period):
            if not all(is_period):
                raise InvalidDateException(
                    title="Invalid model",
                    message="Temporal models should only contain date keys. "
                    f"Invalid date(s): {','.join(is_not_period_keys)}",
                )
            return True
    return False


def convert_date_to_datetime(d: date | datetime) -> datetime:
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def default_temporal_model(data: Any, default_period: Period) -> dict[Period, Any] | None:
    """Ensure the data is a time dependent dict. Also convert all dates to datetime with default time 00:00:00
    :param default_period: the period to use as default
    :param data:
    :return:
    """
    if data is None:
        return None
    elif is_temporal_model(data):
        # Already a temporal model dictionary. Convert all keys to periods if they are dates
        if isinstance(next(iter(data)), date):
            _dates = [convert_date_to_datetime(key) for key in data.keys()] + [datetime.max.replace(microsecond=0)]
            return {
                Period(start=start_date, end=end_date): value
                for start_date, end_date, value in zip(_dates[:-1], _dates[1:], data.values())
            }
        return {
            Period(start=convert_date_to_datetime(key.start), end=convert_date_to_datetime(key.end)): value
            for key, value in data.items()
        }
    else:
        # Set default start
        return {
            default_period: data,
        }
