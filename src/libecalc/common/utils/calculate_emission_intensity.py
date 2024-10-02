from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesCalendarDayRate,
    TimeSeriesVolumesCumulative,
)


def compute_emission_intensity_yearly(
    emission_cumulative: List[float],
    hydrocarbon_export_cumulative: List[float],
    periods: Periods,
) -> List[float]:
    """Standard emission intensity at time k, is the sum of emissions from startup until time k
    divided by the sum of export from startup until time k.
    Thus, intensity_k = ( sum_t=1:k emission(t) ) / ( sum_t=1:k export(t) ).

    The yearly emission intensity for year k is the sum of emissions in year k divided by
    the sum of export in year k (and thus independent of the years before year k)
    I.e. intensity_yearly_k = emission_year_k / export_year_k
    emission_year_k may be computed as emission_cumulative(1. january year=k+1) - emission_cumulative(1. january year=k)
    hcexport_year_k may be computed as hcexport_cumulative(1. january year=k+1) - hcexport_cumulative(1. january year=k)
    To be able to evaluate cumulative emission and hydrocarbon_export at 1. january each year, a linear interpolation function
    is created between the time vector and the cumulative function. To be able to treat time as the x-variable, this is
    first converted to number of seconds from the beginning of the time vector
    """
    df = pd.DataFrame(
        index=[periods.period.start] + periods.end_dates,
        data=list(zip([0.0] + emission_cumulative, [0.0] + hydrocarbon_export_cumulative)),
        columns=["emission_cumulative", "hydrocarbon_cumulative"],
    )

    time_vector_interpolated = pd.date_range(
        start=datetime(periods.periods[0].start.year, 1, 1),
        end=datetime(periods.periods[-1].end.year + 1, 1, 1),
        freq="YS",
    )

    # Linearly interpolating by time using the built-in functionality in Pandas.
    cumulative_interpolated: Optional[pd.DataFrame] = df.reindex(
        sorted(set(periods.all_dates).union(time_vector_interpolated))
    ).interpolate("time")

    if cumulative_interpolated is None:
        raise ValueError("Time interpolation of cumulative yearly emission intensity failed")

    cumulative_yearly = cumulative_interpolated.bfill().loc[time_vector_interpolated]

    emissions_per_year = np.diff(cumulative_yearly.emission_cumulative)
    hcexport_per_year = np.diff(cumulative_yearly.hydrocarbon_cumulative)

    yearly_emission_intensity = np.divide(
        emissions_per_year,
        hcexport_per_year,
        out=np.full_like(emissions_per_year, fill_value=np.nan),
        where=hcexport_per_year != 0,
    )

    return yearly_emission_intensity.tolist()


def compute_emission_intensity_by_yearly_buckets(
    emission_cumulative: TimeSeriesVolumesCumulative,
    hydrocarbon_export_cumulative: TimeSeriesVolumesCumulative,
) -> TimeSeriesCalendarDayRate:
    """Legacy code that computes yearly intensity and casts the results back to the original time-vector.

    TODO: I am a bit confused about the purpose of this function in a period context. Revisit.
    """

    periods = emission_cumulative.periods
    yearly_buckets = range(periods.periods[0].start.year, periods.periods[-1].end.year + 1)
    yearly_intensity = compute_emission_intensity_yearly(
        emission_cumulative=emission_cumulative.values,
        hydrocarbon_export_cumulative=hydrocarbon_export_cumulative.values,
        periods=periods,
    )
    return TimeSeriesCalendarDayRate(
        periods=periods,
        values=[yearly_intensity[yearly_buckets.index(t.start.year)] for t in periods],
        unit=Unit.KG_SM3,
    )
