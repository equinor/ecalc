from math import nan

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.domain.process.compressor.core.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)


def _get_extrapolation_values(
    sorted_sampled_data: pd.DataFrame,
    x_column_name: str,
    function_value_header: str,
) -> tuple[float, float]:
    """Get extrapolation values for the interpolation function f(x). Based on the sampled data the function will only be
    defined within x_min and x_max. This returns the correct extrapolation values so that the function is defined for
    all x values. The extrapolation values might be NaN making the function undefined for that boundary.

    :param sorted_sampled_data: the sampled data describing the compressor model
    :param x_column_name: the name of x in sorted_sampled_data, i.e. Ps, Pd or rate
    :param function_value_header: the name of y in sorted_sampled_data, i.e. FUEL or POWER
    :return: a tuple representing the extrapolation values for the function (f(x) when x < x_min, f(x) when x > x_max),
    The extrapolation values can be NaN.
    """
    if x_column_name == PS_NAME:
        y_at_maximum_x = sorted_sampled_data[function_value_header].iloc[-1]
        return nan, y_at_maximum_x
    else:
        y_at_minimum_x = sorted_sampled_data[function_value_header].iloc[0]
        return y_at_minimum_x, nan


def _get_variable_column_name(sampled_data: pd.DataFrame, allowed_x_names: list[str]) -> str:
    """Find the column name of the variable in sampled data
    :param sampled_data:
    :param allowed_x_names: the possible values for the column representing x in the interpolation function (y = f(x))
    :return: (the name of x column, the name of y column) where y = f(x) is the interpolation function.
    """
    first_column_name: str = str(sampled_data.columns[0])  # Columns could be non-string type
    second_column_name: str = str(sampled_data.columns[1])
    if first_column_name in allowed_x_names:
        return first_column_name
    elif second_column_name in allowed_x_names:
        return second_column_name
    else:
        raise IllegalStateException(
            f"Invalid column names, got '{first_column_name}' and '{second_column_name}', expected {allowed_x_names}"
        )


class CompressorModelSampled1D:
    """Compressor/Pump energy function based on sampled data with only one non-degenerated variable.

    The non-degenerated variable can be either suction pressure (Ps), discharge pressure (Pd) or rate. The energy usage
    is calculated by interpolating the sample data, giving a function power/fuel = f(Ps|Pd|rate).

    Handling of values outside sample data range:

    In the case of rate we simulate ASV recycle by adding fill values equal to the lowest rate in the sample data for
    rates below the lowest rate in the sample data i.e. f(new_rate) = f(minimum_rate), new_rate < minimum_rate. Rates
    above the upper boundary (rate[-1]) is NaN.

    In the case of Pd we simulate a valve after the Compressor/Pump which results in the same behavior as rate. I.e. if
    Pd is too low we can increase it in the Compressor/Pump, then 'fix' the Pd by having a valve lower the pressure.

    In the case of Ps we simulate a valve in front of the Compressor/Pump by adding fill values equal to the highest Ps
    in the sample data i.e. f(new_Ps) = f(max_Ps), new_Ps > max_Ps. If Ps is too high we can lower it with a valve in
    front, then increase the pressure in the Compressor/Pump to the target Pd.
    """

    x_names = [RATE_NAME, PS_NAME, PD_NAME]

    def __init__(self, sampled_data: pd.DataFrame, function_header: str):
        self._x_column_name = _get_variable_column_name(sampled_data, CompressorModelSampled1D.x_names)

        sorted_sampled_data: pd.DataFrame = sampled_data.sort_values(by=self._x_column_name)

        fill_value = _get_extrapolation_values(sorted_sampled_data, self._x_column_name, function_header)

        self._max_rate: float | None = (
            sorted_sampled_data[self._x_column_name].iloc[-1] if self._x_column_name == RATE_NAME else None
        )

        # Check uniqueness of variable values to avoid potential errors when scipy.interpolate sort variable values
        # Check that rate column unique values
        all_variable_values_unique = len(sorted_sampled_data[self._x_column_name]) == len(
            set(sorted_sampled_data[self._x_column_name])
        )
        if not all_variable_values_unique:
            seen = set()
            duplicates = [
                x
                for x in sorted_sampled_data[self._x_column_name]
                if x in seen or seen.add(x)  # type: ignore[func-returns-value]
            ]
            msg = (
                f"1D compressor sampled data require unique variable input values. "
                f"I got non-unique {self._x_column_name} values "
                f'{", ".join(duplicates)}'
            )
            logger.error(msg)
            raise IllegalStateException(msg)

        self._energy_function = interp1d(
            x=sorted_sampled_data[self._x_column_name],
            y=sorted_sampled_data[function_header],
            bounds_error=False,
            fill_value=fill_value,
            assume_sorted=True,
        )

    @property
    def support_max_rate(self) -> bool:
        return bool(self._x_column_name == RATE_NAME)

    def evaluate(
        self,
        rate: NDArray[np.float64] | None = None,
        suction_pressure: NDArray[np.float64] | None = None,
        discharge_pressure: NDArray[np.float64] | None = None,
        **kwargs,
    ) -> NDArray[np.float64]:
        if self._x_column_name == RATE_NAME:
            return np.array(self._energy_function(rate))
        if self._x_column_name == PS_NAME:
            return np.array(self._energy_function(suction_pressure))
        if self._x_column_name == PD_NAME:
            return np.array(self._energy_function(discharge_pressure))
        raise IllegalStateException(
            f"Unknown column name '{self._x_column_name}', allowed column names are '{RATE_NAME}', '{PS_NAME}' or '{PD_NAME}'"
        )

    def get_max_rate(self) -> float | None:
        return self._max_rate
