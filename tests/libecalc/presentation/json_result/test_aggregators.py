from datetime import datetime

import pandas as pd

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.presentation.json_result.aggregators import aggregate_emissions
from libecalc.presentation.json_result.result.emission import PartialEmissionResult


def get_emission_with_only_rate(rates: list[float]) -> TimeSeriesStreamDayRate:
    timesteps = pd.date_range(datetime(2020, 1, 1), datetime(2023, 1, 1), freq="YS").to_pydatetime().tolist()
    periods = Periods.create_periods(
        times=timesteps,
        include_before=False,
        include_after=False,
    )
    return TimeSeriesStreamDayRate(
        periods=periods,
        values=rates,
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )


class TestAggregateEmissions:
    def test_aggregate_emissions(self):
        """Test that emissions are aggregated correctly and that order is preserved."""
        timesteps = pd.date_range(datetime(2020, 1, 1), datetime(2023, 1, 1), freq="YS").to_pydatetime().tolist()
        periods = Periods.create_periods(
            times=timesteps,
            include_before=False,
            include_after=False,
        )
        emissions1 = {
            "CO2": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([1, 2, 3]),
                emission_name="CO2",
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([2, 3, 4]),
                emission_name="CH4",
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
        }
        emissions2 = {
            "CO2:": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([3, 6, 9]),
                emission_name="CO2",
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([4, 8, 12]),
                emission_name="CH4",
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
        }
        aggregated = aggregate_emissions(
            emissions_lists=[emissions1, emissions2],
        )

        assert aggregated["CO2"].rate.values == [4.0, 8.0, 12.0]
        assert aggregated["CH4"].rate.values == [6.0, 11.0, 16.0]

        aggregated_emission_names = list(aggregated)

        assert aggregated_emission_names[0] == "CO2"
        assert aggregated_emission_names[1] == "CH4"
