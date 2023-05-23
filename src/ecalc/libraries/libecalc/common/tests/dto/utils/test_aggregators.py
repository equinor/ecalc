from typing import List

import pandas as pd
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.utils.aggregators import aggregate_emissions


def get_emission_with_only_rate(rates: List[float], name: str):
    timesteps = list(pd.date_range(start="2020-01-01", freq="Y", periods=len(rates)))
    return EmissionResult(
        rate=TimeSeriesRate(
            timesteps=timesteps,
            values=rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ),
        timesteps=timesteps,
        name=name,
        tax=TimeSeriesRate(
            timesteps=timesteps,
            values=[0] * len(rates),
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
        ),
        quota=TimeSeriesRate(
            timesteps=timesteps,
            values=[0] * len(rates),
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
        ),
    )


class TestAggregateEmissions:
    def test_aggregate_emissions(self):
        """Test that emissions are aggregated correctly and that order is preserved."""
        emissions1 = {
            "CO2": get_emission_with_only_rate([1, 2, 3], name="CO2"),
            "CH4": get_emission_with_only_rate([2, 3, 4], name="CH4"),
        }
        emissions2 = {
            "CO2:": get_emission_with_only_rate([3, 6, 9], name="CO2"),
            "CH4": get_emission_with_only_rate([4, 8, 12], name="CH4"),
        }
        aggregated = aggregate_emissions(
            emissions_lists=[emissions1, emissions2],
        )

        assert aggregated["CO2"].rate.values == [4.0, 8.0, 12.0]
        assert aggregated["CH4"].rate.values == [6.0, 11.0, 16.0]

        aggregated_emission_names = list(aggregated)

        assert aggregated_emission_names[0] == "CO2"
        assert aggregated_emission_names[1] == "CH4"
