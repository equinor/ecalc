from __future__ import annotations

import math
from abc import ABC
from collections import defaultdict
from collections.abc import Iterable, Iterator
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Generic,
    Self,
    TypeVar,
    Union,
)

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.logger import logger
from libecalc.common.string.string_utils import to_camel_case
from libecalc.common.time_utils import (
    Frequency,
    Period,
    Periods,
    calculate_delta_days,
    resample_periods,
)
from libecalc.common.units import Unit, UnitConstants

TimeSeriesValue = TypeVar("TimeSeriesValue", bound=Union[int, float, bool, str])


class RateType(str, Enum):
    STREAM_DAY = "STREAM_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"


class Rates:
    @staticmethod
    def to_stream_day(calendar_day_rates: NDArray[np.float64], regularity: list[float]) -> NDArray[np.float64]:
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
    def to_calendar_day(stream_day_rates: NDArray[np.float64], regularity: list[float]) -> NDArray[np.float64]:
        """Convert (production) rate from stream day to calendar day.

        Args:
            stream_day_rates: The production rate in stream day rates
            regularity: The regularity (floats in the range <0,1])

        Returns:
            The corresponding calendar day rates
        """
        return stream_day_rates * np.asarray(regularity, dtype=np.float64)

    @staticmethod
    def to_volumes(
        rates: list[float] | list[TimeSeriesValue] | NDArray[np.float64],
        periods: Periods,
    ) -> NDArray[np.float64]:
        """
        Computes the volume in given periods from the corresponding rates.
        Note that the code does not perform any interpolation or extrapolation,
        it assumes that all periods follow each other, and that the rates are constant within each period.

        Args:
            rates: Production rates, assumed to be constant between dates
            periods: Periods for which the production rates are defined

        Returns:
            The production volume for each period
        """

        delta_days = [
            (period.end - period.start).total_seconds() / UnitConstants.SECONDS_IN_A_DAY for period in periods
        ]
        return np.array([rate * days for rate, days in zip(rates, delta_days)])

    @staticmethod
    def compute_cumulative(volumes: list[float] | NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Compute cumulative volumes from a list of periodic volumes

        Args:
            volumes: Production volume for time periods

        Returns:
            The cumulative sum of the periodic production volumes given as input
        """
        return np.nancumsum(volumes)

    @staticmethod
    def compute_cumulative_volumes_from_daily_rates(
        rates: list[float] | list[TimeSeriesValue] | NDArray[np.float64], periods: Periods
    ) -> NDArray[np.float64]:
        """
        Compute cumulative production volumes based on production rates and the corresponding time periods.
        The production rates are assumed to be constant within each period.

        Args:
            rates: Production rates, assumed to be constant for all periods.
            periods: The periods for which the given production rates are defined.

        Returns:
            The cumulative production volumes
        """
        if rates is None or len(rates) == 0:
            raise ValueError("Failed to compute cumulative volumes from daily rates. Valid rates not provided")
        volumes = Rates.to_volumes(rates=rates, periods=periods)
        return Rates.compute_cumulative(volumes)


class TimeSeries(BaseModel, Generic[TimeSeriesValue], ABC):
    periods: Periods
    values: list[TimeSeriesValue]
    unit: Unit
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True, extra="forbid")

    @field_validator("values")
    @classmethod
    def period_values_one_to_one(cls, v: list[TimeSeriesValue], info: ValidationInfo):
        periods = info.data["periods"]
        nr_periods = len(periods)
        nr_values = len(v)

        if nr_periods != nr_values:
            raise ValueError(
                "Time series: number of periods do not match number "
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

    @property
    def period(self):
        return Period(start=self.periods.periods[0].start, end=self.periods.periods[-1].end)

    @property
    def first_date(self):
        return self.period.start

    @property
    def last_date(self):
        return self.period.end

    @property
    def all_dates(self) -> list[datetime]:
        return self.start_dates + [self.last_date]

    @property
    def start_dates(self):
        return [period.start for period in self.periods]

    @property
    def end_dates(self):
        return [period.end for period in self.periods]

    @property
    def max(self):
        return max(self.values)

    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True) -> Self:
        """
        Resample using forward-fill This means that a value is assumed to be the same until the next observation,
        e.g. covering the whole period interval.

        Args:
            freq: The frequency the time series should be resampled to
            include_start_date: Whether to include the start date if it is not part of the requested reporting frequency
            include_end_date: Whether to include the end date if it is not part of the requested reporting frequency

        Returns:
            TimeSeries resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.periods, self.values

        ds = pd.Series(index=self.start_dates, data=self.values)
        new_periods = resample_periods(
            self.periods, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        new_time_steps = new_periods.start_dates
        ds_resampled = ds.reindex(new_time_steps).ffill()

        return self.__class__(
            periods=new_periods,
            values=ds_resampled.values.tolist(),
            unit=self.unit,
        )

    def extend(self, other: TimeSeries) -> Self:
        """Extend the time series with another time series.
        The two time series needs to follow immediately after each other in time.

        Args:
            other: The time series to extend with

        Returns:
            The extended time series
        """
        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != `{other.unit}`")

        if len(self) > 0 and len(other) > 0:
            if self.last_date != other.first_date and self.first_date != other.last_date:
                raise ValueError("Can not extend two TimeSeries when there is a gap in time between them.")
            if self.last_date == other.first_date:
                return self.__class__(
                    periods=self.periods + other.periods,
                    values=self.values + other.values,
                    unit=self.unit,
                )
        return self.__class__(
            periods=other.periods + self.periods,
            values=other.values + self.values,
            unit=self.unit,
        )

    def merge(self, other: TimeSeries) -> Self:
        """
        Merge two TimeSeries with differing periods

        The periods need to be non-overlapping and follow right after each other

        Args:
            other:

        Returns:

        """
        if not isinstance(other, type(self)):
            raise ValueError(f"Can not merge {type(self)} with {type(other)}")

        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != '{other.unit}'")

        if Period.intersects(self.period, other.period) != 0:
            raise ValueError("Can not merge two TimeSeries with overlapping periods.")

        if self.first_date != other.last_date and self.last_date != other.first_date:
            raise ValueError("Can not merge two TimeSeries when there is a gap in time between them.")

        if self.first_date < other.last_date:
            first = self
            second = other
        else:
            first = other
            second = self

        merged_periods = first.periods + second.periods
        merged_values = first.values + second.values

        return self.__class__(
            periods=merged_periods,
            values=merged_values,
            unit=self.unit,
        )

    def datapoints(self) -> Iterator[tuple[Period, TimeSeriesValue]]:
        yield from zip(self.periods, self.values)

    def for_period(self, period: Period) -> Self:
        """The time series for a given period. The given period needs to have start and end dates that are within the
        start and end dates of the periods in the original time series.

        Args:
            period:

        Returns:

        """
        if period.start not in self.periods.all_dates or period.end not in self.periods.all_dates:
            raise ValueError(
                f"Can not get time series for period {period}. "
                f"The period start and end dates needs to be within the start and end dates of the original time series."
            )
        start_index, end_index = period.get_period_indices(self.periods)
        return self.__class__(
            periods=Periods(self.periods.periods[start_index:end_index]),
            values=self.values[start_index:end_index],
            unit=self.unit,
        )

    def for_periods(self, periods: Periods) -> Self:
        """

        Args:
            periods:

        Returns:

        """
        if not all(
            period.start in self.periods.all_dates and period.end in self.periods.all_dates for period in periods
        ):
            raise ValueError(
                f"Can not get time series for periods {periods}. "
                f"The period start and end dates needs to be within the start and end dates of the original time series."
            )
        start_index, end_index = periods.period.get_period_indices(self.periods)
        return self.__class__(
            periods=Periods(self.periods.periods[start_index:end_index]),
            values=self.values[start_index:end_index],
            unit=self.unit,
        )

    def to_unit(self, unit: Unit) -> Self:
        if unit == self.unit:
            return self.model_copy()
        return self.model_copy(update={"values": [self.unit.to(unit)(rate) for rate in self.values], "unit": unit})

    def forward_fill(self) -> Self:
        return self.model_copy(update={"values": pd.Series(self.values).ffill().tolist()})

    def fill_nan(self, fill_value: float) -> Self:
        return self.model_copy(update={"values": pd.Series(self.values).fillna(fill_value).tolist()})

    def __getitem__(self, indices: slice | int | list[int]) -> Self:
        if isinstance(indices, slice):
            return self.__class__(
                periods=Periods(self.periods.periods[indices]), values=self.values[indices], unit=self.unit
            )
        elif isinstance(indices, int):
            return self.__class__(
                periods=Periods([self.periods.periods[indices]]), values=[self.values[indices]], unit=self.unit
            )
        elif isinstance(indices, list):
            return self.__class__(
                periods=Periods([self.periods.periods[i] for i in indices]),
                values=[self.values[i] for i in indices],
                unit=self.unit,
            )
        raise ValueError(
            f"Unsupported indexing operation. Got '{type(indices)}', expected indices as a slice, single index or a list of indices"
        )

    def __setitem__(self, indices: slice | int | list[int], values: TimeSeriesValue | list[TimeSeriesValue]) -> None:
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

    def fill_values_for_new_periods(
        self,
        new_periods: Iterable[Period],
        fillna: float | str | bool | int,
    ) -> TimeSeries:
        """Based on a consumer time function result (EnergyFunctionResult), the corresponding time vector and
        the consumer time vector, we calculate the actual consumer (consumption) rate.
        """
        for period in self.periods:
            if period not in new_periods:
                raise ValueError(
                    f"You can not alter the existing periods. This is not resampling. Period {period} is not part of the new periods."
                )
        new_values: defaultdict[Period, float | str] = defaultdict(float)
        new_values.update({t: fillna for t in new_periods})
        for t, v in zip(self.periods, self.values):
            if t in new_values:
                new_values[t] = v

        return self.__class__(periods=new_periods, values=new_values.values(), unit=self.unit)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeries):
            return NotImplemented
        return bool(
            # Check that all values are either both NaN or equal
            all(np.isnan(other) and np.isnan(this) or other == this for this, other in zip(self.values, other.values))
            and self.periods == other.periods
            and self.unit == other.unit
        )


class TimeSeriesString(TimeSeries[str]): ...


class TimeSeriesInt(TimeSeries[int]): ...


class TimeSeriesBoolean(TimeSeries[bool]):
    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True) -> Self:
        """
        If a period between two time steps in the return time vector contains more than one time step in the
        original vector, check if any of the relevant values in the time original time vector is False. Then the
        resampled value for that time step will be False.

        Args:
            freq: The frequency the time series should be resampled to
            include_start_date: Whether to include the start date if it is not part of the requested reporting frequency
            include_end_date: Whether to include the end date if it is not part of the requested reporting frequency

        Returns:
            TimeSeriesBoolean resampled to the given frequency
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        new_periods = resample_periods(
            self.periods, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        resampled = []

        # Iterate over all pairs of subsequent dates in the new time vector
        for period in new_periods:
            start_index = self.all_dates.index(max([date for date in self.all_dates if date <= period.start]))
            end_index = self.all_dates.index(max([date for date in self.all_dates if date < period.end]))
            resampled.append(all(self.values[start_index : end_index + 1]))

        return TimeSeriesBoolean(
            periods=new_periods,
            values=resampled,
            unit=self.unit,
        )

    def __mul__(self, other: object) -> Self:
        if not isinstance(other, TimeSeriesBoolean):
            raise TypeError(
                f"TimeSeriesBoolean can only be multiplied by another TimeSeriesBoolean. Received type '{str(other.__class__)}'."
            )

        return self.__class__(
            periods=self.periods,
            values=[self_item and other_item for self_item, other_item in zip(self.values, other.values)],
            unit=self.unit,
        )


class TimeSeriesFloat(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any) -> list[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v


class TimeSeriesVolumesCumulative(TimeSeries[float]):
    """This will represent the sum of the volumes in all periods up to and including each individual period."""

    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any) -> list[TimeSeriesValue]:
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
            freq: The frequency the time series should be resampled to or the Periods to resample to
            include_start_date: Whether to include the start date if it is not part of the requested reporting frequency
            include_end_date: Whether to include the end date if it is not part of the requested reporting frequency

        Returns:
            TimeSeriesVolumesCumulative resampled to the given frequency or given Periods
        """
        if freq is Frequency.NONE:
            return self.model_copy()

        ds = pd.Series(index=self.all_dates, data=[0] + self.values)  # cumulative volume always zero at start date
        new_periods = resample_periods(
            self.periods, frequency=freq, include_start_date=include_start_date, include_end_date=include_end_date
        )
        new_dates = new_periods.all_dates
        if ds.index[-1] not in new_dates:
            logger.warning(
                f"The final date in the rate input ({ds.index[-1].strftime('%m/%d/%Y')}) does not "
                f"correspond to the end of a period with the requested output frequency. There is a "
                f"possibility that the resampling will drop volumes."
            )
        ds_interpolated = ds.reindex(ds.index.union(new_dates)).interpolate("slinear")

        # New resampled pd.Series
        resampled: list[float] = ds_interpolated.reindex(new_dates).values.tolist()

        if not include_start_date:
            dropped_cumulative_volume = resampled[0]
            resampled = [value - dropped_cumulative_volume for value in resampled[1:]]
        else:
            resampled = resampled[1:]

        return TimeSeriesVolumesCumulative(
            periods=new_periods,
            values=resampled,
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
            periods=self.periods,
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

        The first volume will be the cumulative volume for the first period.
        The remaining volumes will be the difference between the cumulative volume at the end of the current period
        and the cumulative volume at the end of the previous period.

        Returns:
            Periodic production volumes
        """
        period_volumes = np.diff([0.0] + self.values).tolist()
        return TimeSeriesVolumes(periods=self.periods, values=period_volumes, unit=self.unit)


class TimeSeriesVolumes(TimeSeries[float]):
    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any) -> list[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    def resample(self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True):
        """
        Resample the time series of period volumes to a new frequency or set of periods.

        This method first converts the time series to cumulative volumes, resamples the cumulative volumes,
        and then converts the resampled cumulative volumes back to period volumes.

        Args:
            freq (Frequency): The new frequency to resample to.
            include_start_date (bool, optional): Whether to include the start date in the resampled periods. Defaults to True.
            include_end_date (bool, optional): Whether to include the end date in the resampled periods. Defaults to True.

        Returns:
            TimeSeriesVolumes: The resampled time series as period volumes.
        """
        return self.cumulative().resample(freq, include_start_date, include_end_date).to_volumes()

    def cumulative(self) -> TimeSeriesVolumesCumulative:
        """
        Converts periodic volumes to cumulative volumes

        All cumulative volumes will be the sum of all periodic volumes up to (and including) the current period.

        Returns:
            Cumulative production volumes
        """
        return TimeSeriesVolumesCumulative(
            periods=self.periods,
            values=Rates.compute_cumulative(self.values).tolist(),
            unit=self.unit,
        )

    def to_rate(self, regularity: list[float] | None = None) -> TimeSeriesRate:
        """
        Conversion from periodic volumes to average rate for each period.

        Regularity is needed to keep track of correct rate type. Regularity assumed to be 1 if not given.

        Args:
            regularity: The regularity (floats in the range <0,1])

        Returns:
            Average production rate
        """
        if len(self.all_dates) > 1:
            delta_days = calculate_delta_days(np.asarray(self.all_dates)).tolist()
            average_rates = [volume / days for volume, days in zip(self.values, delta_days)]
        else:
            average_rates = self.values
            regularity = [1.0] * len(self.periods)

        return TimeSeriesRate(
            periods=self.periods,
            values=average_rates,
            unit=self.unit.volume_to_rate(),
            regularity=regularity,
            rate_type=RateType.CALENDAR_DAY,
        )

    def __truediv__(self, other: object) -> TimeSeriesCalendarDayRate:
        if not isinstance(other, TimeSeriesVolumes):
            raise TypeError(f"Dividing TimeSeriesVolumes by '{str(other.__class__)}' is not supported.")

        if self.unit == Unit.KILO and other.unit == Unit.STANDARD_CUBIC_METER:
            unit = Unit.KG_SM3
        else:
            raise ProgrammingError(
                f"Unable to divide unit '{self.unit}' by unit '{other.unit}'. Please add unit conversion."
            )

        if len(self.values) != len(other.values):
            raise ValueError(
                f"The lengths of the time series must be the same. Got {len(self.values)} and {len(other.values)}."
            )

        return TimeSeriesCalendarDayRate(
            periods=self.periods,
            values=np.divide(
                self.values,
                other.values,
                out=np.full_like(self.values, fill_value=np.nan),
                where=np.asarray(other.values) != 0.0,
            ).tolist(),
            unit=unit,
        )


class TimeSeriesIntensity(TimeSeries[float]):
    def __init__(
        self,
        emissions: TimeSeriesVolumes | TimeSeriesVolumesCumulative = None,
        hc_export: TimeSeriesVolumes | TimeSeriesVolumesCumulative = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._emissions = emissions
        self._hc_export = hc_export

    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> list[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    def resample(
        self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True
    ) -> TimeSeriesIntensity:
        """
        Re-calculate emission intensity using resampled emissions and hydrocarbon export.
        """
        if freq is not Frequency.YEAR:
            return TimeSeriesIntensity(
                periods=Periods([]),
                values=[],
                unit=self.unit,
            )

        emissions_resampled = self._emissions.resample(freq)
        hc_export_resampled = self._hc_export.resample(freq)
        intensity_resampled = emissions_resampled / hc_export_resampled

        return TimeSeriesIntensity(
            periods=intensity_resampled.periods,
            values=intensity_resampled.values,
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
                periods=self.periods,
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
    Probably not needed, as we want to provide info on regularity etc. for the fixed calendar rate data too
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
    regularity: list[float]

    @field_validator("values", "regularity", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any) -> list[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]
        return v

    @field_validator("regularity")
    @classmethod
    def check_regularity_length(cls, regularity: list[float], info: ValidationInfo) -> list[float]:
        regularity_length = len(regularity)
        periods_length = len(info.data["periods"].periods)
        if regularity_length != periods_length:
            raise ValueError(
                f"Regularity must correspond to nr of periods. Length of periods ({periods_length}) !=  length of regularity ({regularity_length})."
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
                    periods=self.periods,
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
                    periods=self.periods,
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
            periods=self.periods + other.periods,
            values=self.values + other.values,
            unit=self.unit,
            regularity=self.regularity + other.regularity,
            rate_type=self.rate_type,
        )

    def merge(self, other: TimeSeries) -> TimeSeriesRate:
        """
        Merge two TimeSeries with differing periods
        Args:
            other:

        Returns:

        """
        if not isinstance(other, type(self)):
            raise ValueError(f"Can not merge {type(self)} with {type(other)}")

        if self.unit != other.unit:
            raise ValueError(f"Mismatching units: '{self.unit}' != '{other.unit}'")

        if not self.rate_type == other.rate_type:
            raise ValueError(
                "Mismatching rate type. Currently you can not merge stream/calendar day rates with calendar/stream day rates."
            )

        if Period.intersects(self.period, other.period) != 0:
            raise ValueError("Can not merge two TimeSeries with overlapping periods")

        if self.first_date != other.last_date and self.last_date != other.first_date:
            raise ValueError("Can not merge two TimeSeries when there is a gap in time between them")

        if self.first_date < other.last_date:
            first = self
            second = other
        else:
            first = other
            second = self

        merged_periods = first.periods + second.periods
        merged_values = first.values + second.values
        merged_regularity = first.regularity + second.regularity

        return self.__class__(
            periods=merged_periods,
            values=merged_values,
            regularity=merged_regularity,
            unit=self.unit,
            rate_type=self.rate_type,
        )

    def for_period(self, period: Period) -> Self:
        """The time series for a given period. The given period needs to have start and end dates that are within the
        start and end dates of the periods in the original time series.

        Args:
            period:

        Returns:

        """
        if not Period.intersects(self.period, period):
            return self.__class__(
                periods=Periods([]),
                values=[],
                regularity=[],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        start_index, end_index = period.get_period_indices(self.periods)
        return self.__class__(
            periods=Periods(self.periods.periods[start_index:end_index]),
            values=self.values[start_index:end_index],
            regularity=self.regularity[start_index:end_index],
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
            periods=self.periods,
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
            periods=self.periods,
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
            periods=self.periods,
        ).tolist()
        return TimeSeriesVolumes(periods=self.periods, values=volumes, unit=self.unit.rate_to_volume())

    def resample(
        self, freq: Frequency, include_start_date: bool = True, include_end_date: bool = True
    ) -> TimeSeriesRate:
        """
        Resample to average rate. If a period at the given frequency spans multiple input periods, the rate will be a
        weighted average or the rates in those periods. The regularity is also recalculated to reflect the new
        time periods.

        Args:
            freq: The frequency the time series should be resampled to
            include_start_date:
            include_end_date:

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
                    periods=self.periods,
                ).tolist(),
                periods=self.periods,
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
                    periods=self.periods,
                ).tolist(),
                periods=self.periods,
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

    def __getitem__(self, indices: slice | int | list[int] | NDArray[np.float64]) -> TimeSeriesRate:
        if isinstance(indices, slice):
            return self.__class__(
                periods=self.periods[indices],
                values=self.values[indices],
                regularity=self.regularity[indices],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        elif isinstance(indices, int):
            return self.__class__(
                periods=[self.periods[indices]],
                values=[self.values[indices]],
                regularity=[self.regularity[indices]],
                unit=self.unit,
                rate_type=self.rate_type,
            )
        elif isinstance(indices, list | np.ndarray):
            indices = list(indices)
            return self.__class__(
                periods=[self.periods[i] for i in indices],
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
            and self.periods == other.periods
            and self.unit == other.unit
            and self.regularity == other.regularity
            and self.rate_type == other.rate_type
        )

    def reindex(self, new_periods: Periods) -> TimeSeriesRate:
        """
        Ensure to map correct value to correct period in the final resulting time vector.
        """
        reindex_values = self.reindex_time_vector(new_periods)
        return TimeSeriesRate(
            periods=new_periods,
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

        regularity = regularity.for_periods(time_series_stream_day_rate.periods)

        return cls(
            periods=time_series_stream_day_rate.periods,
            values=time_series_stream_day_rate.values,
            unit=time_series_stream_day_rate.unit,
            rate_type=RateType.STREAM_DAY,
            regularity=regularity.values,
        )

    def to_stream_day_timeseries(self) -> TimeSeriesStreamDayRate:
        """Convert to fixed stream day rate timeseries"""
        stream_day_rate = self.to_stream_day()
        return TimeSeriesStreamDayRate(
            periods=stream_day_rate.periods, values=stream_day_rate.values, unit=stream_day_rate.unit
        )
