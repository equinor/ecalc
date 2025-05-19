import numpy as np

from libecalc.common.serializable_chart import ChartCurveDTO
from libecalc.domain.process.chart.compressor import (
    SingleSpeedCompressorChart,
    VariableSpeedCompressorChart,
)


def get_single_speed_equivalent(
    compressor_chart: VariableSpeedCompressorChart, speed: float
) -> SingleSpeedCompressorChart:
    # Return an equivalent "single speed chart" for a given speed in a variable speed compressor chart

    chart_curve_at_speed = compressor_chart.get_curve_by_speed(speed=speed)
    if chart_curve_at_speed is not None:
        return SingleSpeedCompressorChart(chart_curve_at_speed)
    else:
        minimum_actual_volume_rate = compressor_chart.minimum_rate_as_function_of_speed(speed)
        maximum_actual_volume_rate = compressor_chart.maximum_rate_as_function_of_speed(speed)
        speed_curve_below = compressor_chart.closest_curve_below_speed(speed=speed)
        speed_curve_above = compressor_chart.closest_curve_above_speed(speed=speed)

        number_of_points = len(speed_curve_below.rate_values) + len(speed_curve_above.rate_values)
        rate_values = np.linspace(
            start=minimum_actual_volume_rate, stop=maximum_actual_volume_rate, num=number_of_points
        )
        head_and_efficiency_values = [
            compressor_chart.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
                speed=speed,
                rate=rate,
            )
            for rate in rate_values
        ]
        head_values, efficiency_values = (np.asarray(iterable) for iterable in list(zip(*head_and_efficiency_values)))

        return SingleSpeedCompressorChart(
            ChartCurveDTO(
                rate_actual_m3_hour=list(rate_values),
                polytropic_head_joule_per_kg=list(head_values),
                efficiency_fraction=list(efficiency_values),
                speed_rpm=speed,
            )
        )
