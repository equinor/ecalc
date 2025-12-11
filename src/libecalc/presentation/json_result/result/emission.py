from __future__ import annotations

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.presentation.json_result.result.tabular_time_series import (
    TabularTimeSeries,
)


class EmissionResult(TabularTimeSeries):
    """The emissions for a result component."""

    name: str
    rate: TimeSeriesRate
    cumulative: TimeSeriesVolumesCumulative

    def get_cumulative_kg(self) -> TimeSeriesVolumesCumulative:
        """Returns cumulative CO2 emissions in kilograms."""
        return self.rate.to_volumes().to_unit(Unit.KILO).cumulative()
