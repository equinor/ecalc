from __future__ import annotations

import itertools
import math
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    DefaultDict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import numpy
import numpy as np
import pandas as pd
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.logger import logger
from libecalc.common.string.string_utils import to_camel_case
from libecalc.common.time_utils import (
    Frequency,
    Period,
    calculate_delta_days,
    resample_time_steps,
)
from libecalc.common.units import Unit
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Self

TimeSeriesValue = TypeVar("TimeSeriesValue", bound=Union[int, float, bool, str])


class RateType(str, Enum):
    STREAM_DAY = "STREAM_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"


class Rates:
    @staticmethod
    def to_stream_day(calendar_day_rates: NDArray[np.float64], regularity: List[float]) -> NDArray[np.float64]:
        """
        Convert (production) rate from calendar day to stream day

        Args:
            calendar_day_rates: The production rate in calendar day rates
            regularity: The regularity (floats in the range <0,1])

        Returns:
            The corresponding stream day rates
        """
        regularity = np.asarray(regularity, dtype=np.float64)  # type: ignore[assignment]
        return np.divide(calendar_day_rates, regularity, out=np.zeros_like(calendar_day_rates), where=regularity != 0.0)  # type: ignore[comparison-overlap]

    @staticmethod
    def to_calendar_day(stream_day_rates: NDArray[np.float64], regularity: List[float]) -> NDArray[np.float64]:
        """Convert (production) rate from stream day to calendar day.

        Args:
            stream_day_rates: The production rate in stream day rates
            regularity: The regularity (floats in the range <0,1])

        Returns:
            The corresponding calendar day rates
        """
        return stream_day_rates * np.asarray(regularity, dtype=np.float64)

    @staticmethod
    def forward_fill_nan_values(rates: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Forward fill Nan-values

        Args:
            rates: Production rates (possibly containing NaN values)

        Returns:
            The production rates where all NaN values are replaced with the last value that was not NaN
        """
        return np.array(pd.Series(rates).ffill())

    @staticmethod
    def to_volumes(
        rates: Union[List[float], List[TimeSeriesValue], NDArray[np.float64]], time_steps: Iterable[datetime]
    ) -> NDArray[np.float64]:
        """
        Computes the volume between two dates from the corresponding rates, according to the given frequency.
        Note that the code does not perform any interpolation or extrapolation,
        it assumes that all requested dates are present, and that the rates are constant between dates.

        Note that when the number of periodic volumes will be one less than the number of rates

        Args:
            rates: Production rates, assumed to be constant between dates
            time_steps: Dates for the given production rates

        Returns:
            The production volume between the dates in time_steps
        """
        delta_days = calculate_delta_days(time_steps)
        return np.array(np.array(rates[:-1]) * delta_days)

    @staticmethod
    def compute_cumulative(
        volumes: Union[List[float], NDArray[np.float64][float, numpy.dtype[numpy.float64]]]
    ) -> NDArray[np.float64][float, numpy.dtype[numpy.float64]]:
        """
        Compute cumulative volumes from a list of periodic volumes

        The number of cumulative volumes will always be one more than the number of periodic volumes. The first
        cumulative volume will always be set zero.

        Args:
            volumes: Production volume for time periods

        Returns:
            The cumulative sum of the periodic production volumes given as input
        """
        return np.append([0], np.nancumsum(volumes))

    @staticmethod
    def compute_cumulative_volumes_from_daily_rates(
        rates: Union[List[float], List[TimeSeriesValue], NDArray[np.float64]], time_steps: Iterable[datetime]
    ) -> NDArray[np.float64]:
        """
        Compute cumulative production volumes based on production rates and the corresponding dates.
        The production rates are assumed to be constant between the different dates.

        Args:
            rates: Production rates, assumed to be constant between dates
            time_steps: Dates for the given production rates

        Returns:
            The cumulative production volumes
        """
        if rates is None or len(rates) == 0:
            raise ValueError("Failed to compute cumulative volumes from daily rates. Valid rates not provided")
        volumes = Rates.to_volumes(rates=rates, time_steps=time_steps)
        return Rates.compute_cumulative(volumes)


class TimeSeries(BaseModel, Generic[TimeSeriesValue], ABC):
    timesteps: List[datetime]
    values: List[TimeSeriesValue]
    unit: Unit
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True, extra="forbid")

    @field_validator("values", mode="before")
    @classmethod
    def timesteps_values_one_to_one(cls, v: List[Any], info: ValidationInfo):
        nr_timesteps = len(info.data["timesteps"])
        nr_values = len(v)

        if not cls.__name__ == TimeSeriesVolumes.__name__:
            if nr_timesteps != nr_values:
                if all(math.isnan(i) for i in v):
                    # TODO: This should probably be solved another place. Temporary solution to make things run
                    return [math.nan] * len(info.data["timesteps"])
                else:
                    raise ProgrammingError(
                        "Time series: number of timesteps do not match number "
                        "of values. Most likely a bug, report to eCalc Dev Team."
                    )
        return v

    def __len__(self) -> int:
        return len(self.values)

    def __lt__(self, other) -> bool:
        if not isinstance(other, TimeSeries):
            # The binary special methods should return NotImplemented instead of raising errors.
            # https://docs.python.org/3/library/constants.html#NotImplemented
            return NotImplemented

        return all(self_value < other_value for self_value, other_value in zip(self.values, other.values))

    @abstractmethod
    def resample(self, freq: Frequency, include_start_date: bool, include_end_date: bool) -> Self:
        ...

    def extend(self, other: TimeSeries) -> Self:
        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != `{other.unit}`")

        return self.__class__(
            timesteps=self.timesteps + other.timesteps,
            values=self.values + other.values,
            unit=self.unit,
        )

    def merge(self, other: TimeSeries) -> Self:
        """
        Merge two TimeSeries with differing timesteps
        Args:
            other:

        Returns:

        """
        if not isinstance(other, type(self)):
            raise ValueError(f"Can not merge {type(self)} with {type(other)}")

        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != '{other.unit}'")

        if len(set(self.timesteps).intersection(other.timesteps)) != 0:
            raise ValueError("Can not merge two TimeSeries with common timesteps")

        merged_timesteps = sorted(itertools.chain(self.timesteps, other.timesteps))
        merged_values = []

        for timestep in merged_timesteps:
            if timestep in self.timesteps:
                timestep_index = self.timesteps.index(timestep)
                merged_values.append(self.values[timestep_index])
            else:
                timestep_index = other.timesteps.index(timestep)
                merged_values.append(other.values[timestep_index])

        return self.__class__(
            timesteps=merged_timesteps,
            values=merged_values,
            unit=self.unit,
        )

    def datapoints(self) -> Iterator[Tuple[datetime, TimeSeriesValue]]:
        yield from zip(self.timesteps, self.values)

    def for_period(self, period: Period) -> Self:
        start_index, end_index = period.get_timestep_indices(self.timesteps)
        end_index = end_index + 1  # Include end as we need it to calculate cumulative correctly
        return self.__class__(
            timesteps=self.timesteps[start_index:end_index],
            values=self.values[start_index:end_index],
            unit=self.unit,
        )

    def for_timestep(self, current_timestep: datetime) -> Self:
        """
        Get the timeseries data for the single timestep given
        :param current_timestep:
        :return: A timeseries with a single step/value corresponding to the timestep given
        """
        timestep_index = self.timesteps.index(current_timestep)

        return self.__class__(
            timesteps=self.timesteps[timestep_index : timestep_index + 1],
            values=self.values[timestep_index : timestep_index + 1],
            unit=self.unit,
        )

    def for_timesteps(self, timesteps: List[datetime]) -> Self:
        """For a given list of datetime, return corresponding values

        Args:
            timesteps:

        Returns:

        """
        values: List[TimeSeriesValue] = []
        for timestep in timesteps:
            timestep_index = self.timesteps.index(timestep)
            values.append(self.values[timestep_index])

        return self.__class__(timesteps=timesteps, values=values, unit=self.unit)

    def to_unit(self, unit: Unit) -> Self:
        if unit == self.unit:
            return self.model_copy()
        return self.model_copy(update={"values": [self.unit.to(unit)(rate) for rate in self.values], "unit": unit})

    def forward_fill(self) -> Self:
        return self.model_copy(update={"values": pd.Series(self.values).ffill().tolist()})

    def fill_nan(self, fill_value: float) -> Self:
        return self.model_copy(update={"values": pd.Series(self.values).fillna(fill_value).tolist()})

    def __getitem__(self, indices: Union[slice, int, List[int]]) -> Self:
        if isinstance(indices, slice):
            return self.__class__(timesteps=self.timesteps[indices], values=self.values[indices], unit=self.unit)
        elif isinstance(indices, int):
            return self.__class__(timesteps=[self.timesteps[indices]], values=[self.values[indices]], unit=self.unit)
        elif isinstance(indices, list):
            return self.__class__(
                timesteps=[self.timesteps[i] for i in indices],
                values=[self.values[i] for i in indices],
                unit=self.unit,
            )
        raise ValueError(
            f"Unsupported indexing operation. Got '{type(indices)}', expected indices as a slice, single index or a list of indices"
        )

    def __setitem__(
        self, indices: Union[slice, int, List[int]], values: Union[TimeSeriesValue, List[TimeSeriesValue]]
    ) -> None:
        if isinstance(values, list):
            if isinstance(indices, slice):
                self.values[indices] = values
            elif isinstance(indices, list):
                for index, value in zip(indices, values):
                    self.values[index] = value
            else:
                raise ValueError(
                    f"Could not update timeseries, Combination of indices of type '{type(indices)}' and values of type '{type(values)}' is not supported"
                )
        elif isinstance(indices, slice):
            self.values[indices] = [values]
        elif isinstance(indices, list):
            for index in indices:
                self.values[index] = values
        elif isinstance(indices, int):
            self.values[indices] = values
        else:
            raise ValueError(
                f"Could not update timeseries, Combination of indices of type '{type(indices)}' and values of type '{type(values)}' is not supported"
            )

    def reindex_time_vector(
        self,
        new_time_vector: Iterable[datetime],
        fillna: Union[float, str] = 0.0,
    ) -> np.ndarray:
        """Based on a consumer time function result (EnergyFunctionResult), the corresponding time vector and
        the consumer time vector, we calculate the actual consumer (consumption) rate.
        """
        new_values: DefaultDict[datetime, Union[float, str]] = defaultdict(float)
        new_values.update({t: fillna for t in new_time_vector})
        for t, v in zip(self.timesteps, self.values):
            if t in new_values:
                new_values[t] = v
            else:
                logger.warning(
                    "Reindexing consumer time vector and losing data. This should not happen."
                    " Please contact eCalc support."
                )

        return np.array([rate_sum for time, rate_sum in sorted(new_values.items())])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeries):
            return NotImplemented
        return bool(
            # Check that all values are either both NaN or equal
            all(np.isnan(other) and np.isnan(this) or other == this for this, other in zip(self.values, other.values))
            and self.timesteps == other.timesteps
            and self.unit == other.unit
        )

    def append(self, timestep: datetime, value: TimeSeriesValue):
        self.timesteps.append(timestep)
        self.values.append(value)


class TimeSeriesString(TimeSeries[str]):
    def resample(self, freq: Frequency, include_start_date: bool, include_end_date: bool) -> Self:
        """
        Resample using forward-fill This means that a value is assumed to be the same until the next observation,
        e.g. covering the whole period interval.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesString resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.timesteps, data=self.values)

        # New resampled pd.Series
        ds_resampled = ds.resample(freq).ffill()

        return TimeSeriesString(
            timesteps=ds_resampled.index.to_pydatetime().tolist(),
            values=ds_resampled.values.tolist(),
            unit=self.unit,
        )


class TimeSeriesInt(TimeSeries[int]):
    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True) -> Self:
        """
        Resample using forward-fill This means that a value is assumed to be the same until the next observation,
        e.g. covering the whole period interval.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesInt resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.timesteps, data=self.values)

        new_timesteps = resample_time_steps(
            self.timesteps, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        # New resampled pd.Series
        ds_resampled = ds.reindex(new_timesteps).ffill()

        return TimeSeriesInt(
            timesteps=new_timesteps,
            values=list(ds_resampled.values.tolist()),
            unit=self.unit,
        )


class TimeSeriesBoolean(TimeSeries[bool]):
    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True) -> Self:
        """
        If a period between two time steps in the return time vector contains more than one time step in the
        original vector, check if any of the relevant values in the time original time vector is False. Then the
        resampled value for that time step will be False.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesBoolean resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        # Always make new time series WITH end date, but remove it later is not needed
        new_timeseries = resample_time_steps(
            self.timesteps, frequency=freq, include_start_date=include_start_date, include_end_date=True
        )
        resampled = []

        # Iterate over all pairs of subsequent dates in the new time vector
        for start_period, end_period in zip(new_timeseries[:-1], new_timeseries[1:]):
            start_index = self.timesteps.index(max([date for date in self.timesteps if date <= start_period]))
            end_index = self.timesteps.index(max([date for date in self.timesteps if date < end_period]))
            resampled.append(all(self.values[start_index : end_index + 1]))

        if include_end_date:
            resampled.append(self.values[-1])
        else:
            new_timeseries.pop()

        return TimeSeriesBoolean(
            timesteps=new_timeseries,
            values=resampled,
            unit=self.unit,
        )

    def __mul__(self, other: object) -> Self:
        if not isinstance(other, TimeSeriesBoolean):
            raise TypeError(
                f"TimeSeriesBoolean can only be multiplied by another TimeSeriesBoolean. Received type '{str(other.__class__)}'."
            )

        return self.__class__(
            timesteps=self.timesteps,
            values=[self_item and other_item for self_item, other_item in zip(self.values, other.values)],
            unit=self.unit,
        )


class TimeSeriesFloat(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> List[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True) -> Self:
        """
        Resample using forward-fill This means that a value is assumed to be the same until the next observation,
        e.g. covering the whole period interval.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesFloat resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.timesteps, data=self.values)

        new_timeseries = resample_time_steps(
            self.timesteps, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        ds_resampled = ds.reindex(new_timeseries).ffill()

        return self.__class__(
            timesteps=new_timeseries,
            values=[float(x) for x in ds_resampled.values.tolist()],
            unit=self.unit,
        )

    def reindex(self, new_time_vector: Iterable[datetime]) -> Self:
        """
        Ensure to map correct value to correct timestep in the final resulting time vector.
        """
        reindex_values = self.reindex_time_vector(new_time_vector)
        return self.__class__(timesteps=new_time_vector, values=reindex_values.tolist(), unit=self.unit)


class TimeSeriesVolumesCumulative(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> List[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    def resample(
        self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True
    ) -> TimeSeriesVolumesCumulative:
        """
        Resample cumulative production volumes according to given frequency. Since the production rates between
        dates are assumed to be constant, the cumulative production volumes will increase linearly between dates.
        Hence, linear interpolation can be used for the resampling. In particular, slinear is used in order to only
        interpolate, not extrapolate.

        If the final date in self.timeseries does not coincide with a date in the requested frequency, cumulative
        production volumes will potentially be dropped.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesVolumesCumulative resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.timesteps, data=self.values)
        new_timeseries = resample_time_steps(
            self.timesteps, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        if ds.index[-1] not in new_timeseries:
            logger.warning(
                f"The final date in the rate input ({ds.index[-1].strftime('%m/%d/%Y')}) does not "
                f"correspond to the end of a period with the requested output frequency. There is a "
                f"possibility that the resampling will drop volumes."
            )
        ds_interpolated = ds.reindex(ds.index.union(new_timeseries)).interpolate("slinear")

        # New resampled pd.Series
        ds_resampled = ds_interpolated.reindex(new_timeseries)

        return TimeSeriesVolumesCumulative(
            timesteps=new_timeseries,
            # Are we sure this is always an DatetimeIndex? type: ignore
            values=ds_resampled.values.tolist(),
            unit=self.unit,
        )

    def __truediv__(self, other: object) -> TimeSeriesCalendarDayRate:
        if not isinstance(other, TimeSeriesVolumesCumulative):
            raise TypeError(f"Dividing TimeSeriesVolumesCumulative by '{str(other.__class__)}' is not supported.")

        if self.unit == Unit.KILO and other.unit == Unit.STANDARD_CUBIC_METER:
            unit = Unit.KG_SM3
        else:
            raise ProgrammingError(
                f"Unable to divide unit '{self.unit}' by unit '{other.unit}'. Please add unit conversion."
            )
        return TimeSeriesCalendarDayRate(
            timesteps=self.timesteps,
            values=np.divide(
                self.values,
                other.values,
                out=np.full_like(self.values, fill_value=np.nan),
                where=np.asarray(other.values) != 0.0,
            ).tolist(),
            unit=unit,
        )

    def to_volumes(self) -> TimeSeriesVolumes:
        """
        Converts cumulative volumes to period volumes

        The first volume will be the difference between the cumulative volumes at the first two times, and so on
        To keep the same dimension, a volume of zero is always added at the end

        The dimension of periodic volumes will be one less that the dimension of cumulative volumes

        Returns:
            Periodic production volumes
        """
        period_volumes = np.diff(self.values).tolist()
        return TimeSeriesVolumes(timesteps=self.timesteps, values=period_volumes, unit=self.unit)


class TimeSeriesVolumes(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> List[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    @field_validator("values", mode="before")
    def check_length_timestep_values(cls, v: List[Any], info: ValidationInfo):
        # Initially timesteps for volumes contains one more item than values
        # After reindex number of timesteps equals number of values
        # TODO: Ensure periodical volumes are handled in a consistent way. Why different after reindex?
        if len(v) not in [len(info.data["timesteps"]), len(info.data["timesteps"]) - 1]:
            raise ProgrammingError(
                "Time series: number of timesteps do not match number "
                "of values. Most likely a bug, report to eCalc Dev Team."
            )
        return v

    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True):
        msg = (
            f"{self.__class__.__name__} does not have an resample method."
            f" You should not land here. Please contact the eCalc Support."
        )
        logger.warning(msg)
        raise NotImplementedError(msg)

    def reindex(self, time_steps: List[datetime]) -> Self:
        """
        This is legacy code where the time steps are in reality periods. time_steps[0] and time_steps[1] is period 1
        and corresponds to value[0].

        Note: we do not allow up-sampling, hence the ValueError if a new value is discovered within the existing
            time-vector.
        """
        for time_step in time_steps:
            if self.timesteps[0] <= time_step <= self.timesteps[-1] and time_step not in self.timesteps:
                raise ValueError(f"Could not reindex volumes. Missing time step `{time_step}`.")

        cumulative_volumes = Rates.compute_cumulative(self.values)

        re_indexed_cumulative_values = pd.Series(index=self.timesteps, data=cumulative_volumes).reindex(time_steps)

        # Diffing cumulative volume in order to go back to volumes per period.
        re_indexed_volumes = re_indexed_cumulative_values.diff().shift(-1)[:-1]

        return self.__class__(
            timesteps=re_indexed_volumes.index.to_pydatetime().tolist(),
            values=re_indexed_volumes.tolist(),
            unit=self.unit,
        )

    def cumulative(self) -> TimeSeriesVolumesCumulative:
        """
        Converts periodic volumes to cumulative volumes

        The first volume will always be zero. All other volumes will be the sum of all periodic volumes up to the
        time in question.

        The dimension of cumulative volumes will be one more that the dimension of periodic volumes.

        Returns:
            Cumulative production volumes
        """
        return TimeSeriesVolumesCumulative(
            timesteps=self.timesteps,
            values=Rates.compute_cumulative(self.values).tolist(),
            unit=self.unit,
        )

    def to_rate(self, regularity: Optional[List[float]] = None) -> TimeSeriesRate:
        """
        Conversion from periodic volumes to average rate for each period.

        Regularity is needed to keep track of correct rate type. Regularity assumed to be 1 if not given.

        The dimension of periodic volumes is one less than the number of time steps. Hence, a rate of zero is added
        at the end to make dimensions equal. The regularity may also need an additional value to have the same
        dimension as the average rates and the number of time steps.

        Args:
            regularity: The regularity (floats in the range <0,1])

        Returns:
            Average production rate
        """
        if len(self.timesteps) > 1:
            delta_days = calculate_delta_days(self.timesteps).tolist()
            average_rates = [volume / days for volume, days in zip(self.values, delta_days)]

            if regularity is not None and isinstance(regularity, list) and len(regularity) == len(self.timesteps) - 1:
                regularity.append(0.0)
            average_rates.append(0.0)
        else:
            average_rates = self.values
            regularity = [1.0] * len(self.timesteps)

        return TimeSeriesRate(
            timesteps=self.timesteps,
            values=average_rates,
            unit=self.unit.volume_to_rate(),
            regularity=regularity,
            rate_type=RateType.CALENDAR_DAY,
        )


class TimeSeriesIntensity(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> List[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    def resample(
        self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True
    ) -> TimeSeriesIntensity:
        """
        Resample emission intensity according to given frequency.
        Slinear is used in order to only interpolate, not extrapolate.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesIntensity resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.timesteps, data=self.values)
        new_timeseries = resample_time_steps(
            self.timesteps, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        ds_interpolated = ds.reindex(ds.index.union(new_timeseries)).interpolate("slinear")

        # New resampled pd.Series
        ds_resampled = ds_interpolated.reindex(new_timeseries)

        return TimeSeriesIntensity(
            timesteps=new_timeseries,
            values=ds_resampled.to_numpy().tolist(),
            unit=self.unit,
        )


class TimeSeriesStreamDayRate(TimeSeriesFloat):
    """
    Domain/core layer only.

    Explicit class for only internal core usage. Makes it easy to catch that the
    type of data is rate, and has been converted to Stream Day for internal usage.

    When used internally, rate is handled as a "point in time float". It is only needed to
    be handled specifically when reporting, e.g. converting to calendar day rate, if needed.
    """

    def __add__(self, other: TimeSeriesStreamDayRate) -> TimeSeriesStreamDayRate:
        """
        Args:
            other:

        Returns:

        """
        # Check for same unit
        if not self.unit == other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != `{other.unit}`")

        if isinstance(other, TimeSeriesStreamDayRate):
            return TimeSeriesStreamDayRate(
                timesteps=self.timesteps,
                values=elementwise_sum(self.values, other.values).tolist(),
                unit=self.unit,
            )
        else:
            raise TypeError(
                f"TimeSeriesRate can only be added to another TimeSeriesRate. Received type '{str(other.__class__)}'."
            )


class TimeSeriesCalendarDayRate(TimeSeriesFloat):
    """
    Application layer only - only calendar day rate/used for reporting
    Probably not needed, as we want to provide info on regularity etc for the fixed calendar rate data too
    """

    ...


class TimeSeriesRate(TimeSeries[float]):
    """A rate time series with can be either in RateType.STREAM_DAY (default) or RateType.CALENDAR_DAY.

    The regularity converts the time series from stream day to calendar day in the following way:
        calendar_day_rate = stream_day_rate * regularity
        stream_day_rate = calendar_day_rate / regularity

    The regularity will be defaulted to 1 if not provided.

    Stream day rates are relevant for quantities where capacity is important (volumes and power).
    """

    rate_type: RateType
    regularity: List[float]

    @field_validator("values", "regularity", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> List[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    @field_validator("regularity")
    def check_regularity_length(cls, regularity: List[float], info: ValidationInfo) -> List[float]:
        regularity_length = len(regularity)
        timesteps_length = len(info.data.get("timesteps", []))
        if regularity_length != timesteps_length:
            raise ProgrammingError(
                f"Regularity must correspond to nr of timesteps. Length of timesteps ({timesteps_length}) !=  length of regularity ({regularity_length})."
            )

        return regularity

    def __add__(self, other: TimeSeriesRate) -> TimeSeriesRate:
        # Check for same unit
        if not self.unit == other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != `{other.unit}`")

        if not self.rate_type == other.rate_type:
            raise ValueError(
                "Mismatching rate type. Currently you can not add stream day rates and calendar day rates."
            )

        if isinstance(other, TimeSeriesRate):
            if self.regularity == other.regularity:
                # Adding TimeSeriesRate with same regularity -> New TimeSeriesRate with same regularity
                return self.__class__(
                    timesteps=self.timesteps,
                    values=elementwise_sum(self.values, other.values).tolist(),
                    unit=self.unit,
                    regularity=self.regularity,
                    rate_type=self.rate_type,
                )
            else:
                # Adding two TimeSeriesRate with different regularity -> New TimeSeriesRate with new regularity
                sum_calendar_day = elementwise_sum(self.to_calendar_day().values, other.to_calendar_day().values)
                sum_stream_day = elementwise_sum(self.to_stream_day().values, other.to_stream_day().values)

                return TimeSeriesRate(
                    timesteps=self.timesteps,
                    values=elementwise_sum(self.values, other.values).tolist(),
                    unit=self.unit,
                    regularity=(sum_calendar_day / sum_stream_day).tolist(),
                    rate_type=self.rate_type,
                )
        else:
            raise TypeError(
                f"TimeSeriesRate can only be added to another TimeSeriesRate. Received type '{str(other.__class__)}'."
            )

    def extend(self, other: TimeSeries) -> Self:
        if not isinstance(other, TimeSeriesRate):
            raise ValueError(
                f"'{str(self.__class__)}' can only be extended with itself, received type '{str(other.__class__)}'"
            )

        # Check for same unit
        if not self.unit == other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != `{other.unit}`")

        if not self.rate_type == other.rate_type:
            raise ValueError(
                "Mismatching rate type. Currently you can not extend stream/calendar day rates with calendar/stream day rates."
            )

        return self.__class__(
            timesteps=self.timesteps + other.timesteps,
            values=self.values + other.values,
            unit=self.unit,
            regularity=self.regularity + other.regularity,
            rate_type=self.rate_type,
        )

    def merge(self, other: TimeSeries) -> TimeSeriesRate:
        """
        Merge two TimeSeries with differing timesteps
        Args:
            other:

        Returns:

        """

        if not isinstance(other, TimeSeriesRate):
            raise ValueError(f"Can not merge {type(self)} with {type(other)}")

        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != '{other.unit}'")

        if not self.rate_type == other.rate_type:
            raise ValueError(
                "Mismatching rate type. Currently you can not merge stream/calendar day rates with calendar/stream day rates."
            )

        if len(set(self.timesteps).intersection(other.timesteps)) != 0:
            raise ValueError("Can not merge two TimeSeries with common timesteps")

        merged_timesteps = sorted(itertools.chain(self.timesteps, other.timesteps))
        merged_values = []
        merged_regularity = []

        for timestep in merged_timesteps:
            if timestep in self.timesteps:
                timestep_index = self.timesteps.index(timestep)
                merged_values.append(self.values[timestep_index])
                if self.regularity is not None:
                    merged_regularity.append(self.regularity[timestep_index])
                else:
                    merged_regularity.append(1)  # whaaaaaaaaaa
            else:
                timestep_index = other.timesteps.index(timestep)
                merged_values.append(other.values[timestep_index])
                if other.regularity is not None:
                    merged_regularity.append(other.regularity[timestep_index])
                else:
                    merged_regularity.append(1)  # whaaaaaaaaaa

        return self.__class__(
            timesteps=merged_timesteps,
            values=merged_values,
            regularity=merged_regularity,
            unit=self.unit,
            rate_type=self.rate_type,
        )

    def for_period(self, period: Period) -> Self:
        start_index, end_index = period.get_timestep_indices(self.timesteps)
        end_index = end_index + 1  # Include end as we need it to calculate cumulative correctly
        return self.__class__(
            timesteps=self.timesteps[start_index:end_index],
            values=self.values[start_index:end_index],
            regularity=self.regularity[start_index:end_index],
            unit=self.unit,
            rate_type=self.rate_type,
        )

    def for_timestep(self, current_timestep: datetime) -> Self:
        """
        Get the timeseries data for the single timestep given
        :param current_timestep:
        :return: A timeseries with a single step/value corresponding to the timestep given
        """
        timestep_index = self.timesteps.index(current_timestep)
        return self.__class__(
            timesteps=self.timesteps[timestep_index : timestep_index + 1],
            values=self.values[timestep_index : timestep_index + 1],
            regularity=self.regularity[timestep_index : timestep_index + 1],
            unit=self.unit,
            rate_type=self.rate_type,
        )

    def to_calendar_day(self) -> Self:
        """Convert rates to calendar day rates."""
        if self.rate_type == RateType.CALENDAR_DAY:
            return self

        calendar_day_rates = Rates.to_calendar_day(
            stream_day_rates=np.asarray(self.values),
            regularity=self.regularity,
        ).tolist()
        return self.__class__(
            timesteps=self.timesteps,
            values=calendar_day_rates,
            regularity=self.regularity,
            unit=self.unit,
            rate_type=RateType.CALENDAR_DAY,
        )

    def to_stream_day(self) -> Self:
        """Convert rates to stream day rates."""
        if self.rate_type == RateType.STREAM_DAY:
            return self

        stream_day_rates = Rates.to_stream_day(
            calendar_day_rates=np.asarray(self.values),
            regularity=self.regularity,
        ).tolist()
        return self.__class__(
            timesteps=self.timesteps,
            values=stream_day_rates,
            regularity=self.regularity,
            unit=self.unit,
            rate_type=RateType.STREAM_DAY,
        )

    def to_volumes(self) -> TimeSeriesVolumes:
        """Convert rates to volumes. After this step the time steps represents periods and should contain one more item
        than the rates vector. This means that the last rate is ignored.

        Volumes are always found from calendar day rates
        """
        volumes = Rates.to_volumes(
            rates=self.to_calendar_day().values,
            time_steps=self.timesteps,
        ).tolist()
        return TimeSeriesVolumes(timesteps=self.timesteps, values=volumes, unit=self.unit.rate_to_volume())

    def resample(
        self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True
    ) -> TimeSeriesRate:
        """
        Resample to average rate. If a period at the given frequency spans multiple input periods, the rate will be a
        weighted average or the rates in those periods. The regularity is also recalculated to reflect the new
        time periods.

        If the final date(s) in self.timesteps does not correspond to a date in the requested output frequency series
        the volumes will be dropped in the resampling. TODO: include these dates as well?

        Note the the rate and regularity are always set to zero at the last time step at the new frequency.
        As this is the last time step it does not really matter what the values are. This is just to make sure that the
        regularity/values/timesteps for the resampled TimeSeriesRate have equal length.

        Args:
            freq: The frequency the time series should be resampled to

        Returns:
            TimeSeriesRate resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        # make resampled calendar day volumes via cumulative calendar day volumes
        calendar_day_volumes = (
            TimeSeriesVolumesCumulative(
                values=Rates.compute_cumulative_volumes_from_daily_rates(
                    rates=self.to_calendar_day().values,
                    time_steps=self.timesteps,
                ).tolist(),
                timesteps=self.timesteps,
                unit=self.to_volumes().unit,
            )
            .resample(freq=freq, include_start_date=include_start_date, include_end_date=include_end_date)
            .to_volumes()
        )
        # make resampled stream day volumes via cumulative "stream-day-volumes"
        stream_day_volumes = (
            TimeSeriesVolumesCumulative(
                values=Rates.compute_cumulative_volumes_from_daily_rates(
                    rates=self.to_stream_day().values,
                    time_steps=self.timesteps,
                ).tolist(),
                timesteps=self.timesteps,
                unit=self.to_volumes().unit,
            )
            .resample(freq=freq, include_start_date=include_start_date, include_end_date=include_end_date)
            .to_volumes()
        )

        # the ratio between calendar day and stream day volumes for a period gives the regularity for that period
        new_regularity = [
            float(cal_day) / float(stream_day) if stream_day != 0.0 else 0.0
            for cal_day, stream_day in zip(calendar_day_volumes.values, stream_day_volumes.values)
        ]

        # go from period volumes to average rate in period (regularity assumed to be 1 if not provided)
        new_time_series = calendar_day_volumes.to_rate(regularity=new_regularity)

        if self.rate_type == RateType.CALENDAR_DAY:
            return new_time_series
        else:
            return new_time_series.to_stream_day()

    def __getitem__(self, indices: Union[slice, int, List[int], NDArray[np.float64]]) -> TimeSeriesRate:
        if isinstance(indices, slice):
            return self.__class__(
                timesteps=self.timesteps[indices],
                values=self.values[indices],
                regularity=self.regularity[indices],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        elif isinstance(indices, int):
            return self.__class__(
                timesteps=[self.timesteps[indices]],
                values=[self.values[indices]],
                regularity=[self.regularity[indices]],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        elif isinstance(indices, (list, np.ndarray)):
            indices = list(indices)
            return self.__class__(
                timesteps=[self.timesteps[i] for i in indices],
                values=[self.values[i] for i in indices],
                regularity=[self.regularity[i] for i in indices],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        raise ValueError(
            f"Unsupported indexing operation. Got '{type(indices)}', expected indices as a slice, single index or a list of indices"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeriesRate):
            raise NotImplementedError
        return bool(
            # Check that all values are either both NaN or equal
            all(np.isnan(other) and np.isnan(this) or other == this for this, other in zip(self.values, other.values))
            and self.timesteps == other.timesteps
            and self.unit == other.unit
            and self.regularity == other.regularity
            and self.rate_type == other.rate_type
        )

    def reindex(self, new_time_vector: Iterable[datetime]) -> TimeSeriesRate:
        """
        Ensure to map correct value to correct timestep in the final resulting time vector.
        """
        reindex_values = self.reindex_time_vector(new_time_vector)
        return TimeSeriesRate(
            timesteps=new_time_vector,
            values=reindex_values.tolist(),
            unit=self.unit,
            regularity=self.regularity,
            rate_type=self.rate_type,
        )

    @classmethod
    def from_timeseries_stream_day_rate(
        cls, time_series_stream_day_rate: TimeSeriesStreamDayRate, regularity: TimeSeriesFloat
    ) -> Self:
        if time_series_stream_day_rate is None:
            return None

        regularity = regularity.for_timesteps(time_series_stream_day_rate.timesteps)

        return cls(
            timesteps=time_series_stream_day_rate.timesteps,
            values=time_series_stream_day_rate.values,
            unit=time_series_stream_day_rate.unit,
            rate_type=RateType.STREAM_DAY,
            regularity=regularity.values,
        )

    def to_stream_day_timeseries(self) -> TimeSeriesStreamDayRate:
        """Convert to fixed stream day rate timeseries"""
        stream_day_rate = self.to_stream_day()
        return TimeSeriesStreamDayRate(
            timesteps=stream_day_rate.timesteps, values=stream_day_rate.values, unit=stream_day_rate.unit
        )
