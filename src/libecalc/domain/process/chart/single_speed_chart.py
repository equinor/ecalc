import numpy as np

from libecalc.domain.process.chart.base import ChartCurve
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag


class SingleSpeedChart(ChartCurve):
    """A single speed chart is just one ChartCurve.

    Here we may implement methods that is not relevant for single chart curves but for a single speed equipment.

    The reason for this subclass is that we already use the naming convention single and variable speed equipment.

    Note: For a single speed chart the speed is optional, but it is good practice to include it.
    """

    def get_chart_area_flag(self, rate: float) -> ChartAreaFlag:
        """Set chart area flag based on rate [Am3/h]."""
        if rate < self.minimum_rate:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
        elif rate > self.maximum_rate:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
        else:
            # For single speed charts, the point is interpreted as internal if rate is between minimum and maximum rate
            chart_area_flag = ChartAreaFlag.INTERNAL_POINT
        return chart_area_flag

    @property
    def minimum_speed(self) -> float:
        """Used to handle single speed and variable speed charts generically."""
        return self.speed_rpm if self.speed_rpm else np.nan

    @property
    def maximum_speed(self) -> float:
        """Used to handle single speed and variable speed charts generically."""
        return self.speed_rpm if self.speed_rpm else np.nan
