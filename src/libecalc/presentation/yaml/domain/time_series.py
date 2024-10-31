from datetime import datetime
from operator import itemgetter
from typing import Self

from scipy.interpolate import interp1d

from libecalc.common.list.list_utils import transpose
from libecalc.dto.types import InterpolationType


class TimeSeries:
    def __init__(
        self,
        reference_id: str,
        time_vector: list[datetime],
        series: list[float],
        extrapolate: bool,
        interpolation_type: InterpolationType,
    ):
        self.reference_id = reference_id
        self.time_vector = time_vector
        self.series = series
        self._extrapolate = extrapolate
        self._interpolation_type = interpolation_type

    @staticmethod
    def _get_interpolation_kind(rate_interpolation_type: InterpolationType) -> str:
        if rate_interpolation_type == InterpolationType.LINEAR:
            return "linear"
        elif rate_interpolation_type == InterpolationType.RIGHT:
            return "previous"
        elif rate_interpolation_type == InterpolationType.LEFT:
            return "next"
        else:
            raise ValueError(f"Invalid interpolation type, got {rate_interpolation_type}.")

    def _interpolate(self, time_vector: list[datetime], rate_interpolation_type: InterpolationType) -> list[float]:
        interpolation_kind = self._get_interpolation_kind(
            rate_interpolation_type=rate_interpolation_type,
        )

        start_time = self.time_vector[0]

        setup_times: list[float]
        if len(self.time_vector) == 1:
            # add dummy time 1 second later
            setup_times = [0, 1]
            setup_y = 2 * self.series
        else:
            # Interpolator x variable is number of seconds from first date time
            setup_times = [(time - start_time).total_seconds() for time in self.time_vector]
            setup_y = self.series

        interpolator = interp1d(x=setup_times, y=setup_y, kind=interpolation_kind)
        target_times = [(time - start_time).total_seconds() for time in time_vector]
        return list(interpolator(target_times))

    def fit_to_time_vector(
        self,
        time_vector: list[datetime],
    ) -> Self:
        start, end = self.time_vector[0], self.time_vector[-1]
        number_of_entries_before, entries_between, number_of_entries_after = split_time_vector(
            time_vector, start=start, end=end
        )

        if self._extrapolate:
            extrapolation_after_value = self.series[-1]
        else:
            extrapolation_after_value = 0.0

        before_values = [0.0] * number_of_entries_before
        between_values = self._interpolate(
            time_vector=entries_between, rate_interpolation_type=self._interpolation_type
        )
        after_values = [extrapolation_after_value] * number_of_entries_after

        return self.__class__(
            reference_id=self.reference_id,
            time_vector=time_vector,
            series=[*before_values, *between_values, *after_values],
            extrapolate=self._extrapolate,
            interpolation_type=self._interpolation_type,
        )

    def sort(self) -> Self:
        sort_columns = [self.time_vector, self.series]
        sort_rows = transpose(sort_columns)
        sorted_rows = sorted(sort_rows, key=itemgetter(0))
        sorted_columns = transpose(sorted_rows)
        self.time_vector = sorted_columns[0]
        self.series = sorted_columns[1]
        return self


def split_time_vector(
    time_vector: list[datetime],
    start: datetime,
    end: datetime,
) -> tuple[int, list[datetime], int]:
    """Find the entries between start and end, also counting the number of entries before start and after end."""
    number_of_entries_before = len([date for date in time_vector if date < start])
    number_of_entries_after = len([date for date in time_vector if date > end])
    entries_between = [date for date in time_vector if start <= date <= end]
    return number_of_entries_before, entries_between, number_of_entries_after
