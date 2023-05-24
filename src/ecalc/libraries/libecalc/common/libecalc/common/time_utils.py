from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from libecalc.common.exceptions import ProgrammingError
from libecalc.common.units import UnitConstants
from numpy.typing import ArrayLike


def calculate_delta_days(time_vector: ArrayLike) -> np.ndarray:
    return np.array([x.total_seconds() / UnitConstants.SECONDS_IN_A_DAY for x in np.diff(time_vector)])


@dataclass
class Period:
    start: datetime = datetime.min
    end: datetime = datetime.max

    def __str__(self) -> str:
        return f"{self.start}:{self.end}"

    def __contains__(self, time: datetime) -> bool:
        return self.start <= time < self.end

    @staticmethod
    def intersects(first: Period, second: Period) -> bool:
        return first.start in second or second.start in first

    def get_timestep_indices(self, timesteps: List[datetime]) -> Tuple[int, int]:
        try:
            start_index = timesteps.index(max(self.start, timesteps[0]))
            if self.end > timesteps[-1]:
                end_index = len(timesteps) + 1
            else:
                end_index = timesteps.index(self.end)

            return start_index, end_index
        except (IndexError, ValueError) as e:
            raise ProgrammingError(
                "Trying to access a timestep index that does not exist. Please contact eCalc support.\n\t"
                f"Period: {self.start}:{self.end} - timesteps: {timesteps}"
            ) from e


@dataclass
class Periods:
    periods: List[Period]

    @classmethod
    def create_periods(cls, times: List[datetime]) -> Periods:
        if len(times) == 0:
            return cls([])

        return cls(
            [
                Period(
                    end=times[0],
                ),
                *[Period(start=times[index], end=times[index + 1]) for index in range(len(times) - 1)],
                Period(start=times[-1]),
            ]
        )

    def get_period(self, time: datetime) -> Period:
        for period in self.periods:
            if time in period:
                return period

        raise ValueError(f"Period for date '{time}' not found in periods")


def define_time_model_for_period(
    time_model_data: Optional[Any], target_period: Period
) -> Optional[Dict[datetime, Any]]:
    """Process time model based on the target period.

    Steps:
        - Add a default start date if the model is not already a time model
        - Filter definitions outside given time period
        - Adjust start_date of the first model to the period
    :param time_model_data: a model that can vary based on time,
        i.e. {1900.01.01: some model, 1950.01.01: some other model}
    :param target_period: period for which a model is defined (START,END specified by user or default to everything)
    :return: the time model for the target period
    """
    if time_model_data is None:
        return None

    # Make sure the model is a time model
    time_model_data = default_temporal_model(time_model_data, default_start=target_period.start)

    model_periods = Periods.create_periods(list(time_model_data.keys()))
    model_periods.periods = model_periods.periods[1:]  # Remove first period (from datetime.min to first model start).

    return {
        max(model_period.start, target_period.start): model
        for model_period, model in zip(model_periods.periods, time_model_data.values())
        if Period.intersects(model_period, target_period)
    }


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


def resample_time_steps(
    time_steps: List[datetime],
    frequency: Frequency,
    remove_last: bool = False,
) -> List[datetime]:
    """Makes a time vector, based on the first and last date in time_vector and the frequency.

    :param time_steps: The original time vector
    :type time_steps: List[datetime]
    :param frequency: The reporting frequency
    :type frequency: Frequency
    :param remove_last: Decides whether the final date should be returned
    :type remove_last: bool
    :return: Time vector with dates according to frequency, start and end date
    "rtype: List[datetime]
    """
    if frequency is not Frequency.NONE:
        time_step_vector = create_time_steps(start=time_steps[0], end=time_steps[-1], frequency=frequency)
    else:
        time_step_vector = time_steps

    return time_step_vector[:-1] if remove_last else time_step_vector


def create_time_steps(frequency: Frequency, start: datetime, end: datetime) -> List[datetime]:
    time_steps = pd.date_range(start=start, end=end, freq=frequency.value)
    return sorted({clear_time(start), *[clear_time(time_step) for time_step in time_steps], clear_time(end)})


def clear_time(d: datetime) -> datetime:
    return datetime.combine(d.date(), datetime.min.time())


def is_temporal_model(data: Dict) -> bool:
    if isinstance(data, dict):
        is_date = []
        for key in data:
            if isinstance(key, date):
                is_date.append(True)
            else:
                try:
                    datetime.strptime(key, "%Y-%m-%dT%H:%M:%S")
                    is_date.append(True)
                except (TypeError, ValueError):
                    is_date.append(False)
        if any(is_date):
            if not all(is_date):
                raise ValueError("Time dependent should only contain date keys")
            return True
    return False


def convert_date_to_datetime(d: Union[date, datetime]) -> datetime:
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def default_temporal_model(data: Any, default_start: datetime) -> Optional[Dict[datetime, Any]]:
    """Ensure the data is a time dependent dict. Also convert all dates to datetime with default time 00:00:00
    :param default_start: the start time to use as default
    :param data:
    :return:
    """
    if data is None:
        return None
    elif is_temporal_model(data):
        # Already a date-dict
        return {convert_date_to_datetime(_date): value for _date, value in data.items()}
    else:
        # Set default start
        return {
            default_start: data,
        }
