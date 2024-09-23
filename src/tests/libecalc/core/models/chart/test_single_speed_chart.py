from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.core.models.chart import SingleSpeedChart


def test_chart_curve_data_setup_from_arrays():
    """Speed defaults to None. This is the only difference between ChartCurve and SingleSpeedChart at the moment."""
    chart_curve_data = SingleSpeedChart(
        SingleSpeedChartDTO(
            rate_actual_m3_hour=[1, 2.0],
            polytropic_head_joule_per_kg=[3, 4.0],
            efficiency_fraction=[0.3, 0.7],
            speed_rpm=1,
        )
    )
    assert chart_curve_data.speed_rpm == 1
