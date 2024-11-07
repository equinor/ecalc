import numpy as np
import pytest

from libecalc.common.serializable_chart import ChartCurveDTO, VariableSpeedChartDTO
from libecalc.core.models.chart import VariableSpeedChart


@pytest.fixture
def variable_speed_chart() -> VariableSpeedChart:
    return VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[1.0, 2.5, 5.5],
                    polytropic_head_joule_per_kg=[4.5, 4.0, 2.5],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=1,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[3.0, 5.0, 7.0],
                    polytropic_head_joule_per_kg=[7.5, 6.0, 5.0],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=2,
                ),
            ]
        )
    )


@pytest.fixture
def variable_speed_chart_multiple_speeds() -> VariableSpeedChart:
    return VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[2900.0, 3504.0, 4003.0, 4595.0],
                    polytropic_head_joule_per_kg=[82531.5, 78440.7, 72240.8, 60105.8],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.7],
                    speed_rpm=7689.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[3306.0, 4000.0, 4499.0, 4997.0, 5242.0],
                    polytropic_head_joule_per_kg=[107429.0, 101955.0, 95225.6, 84307.1, 78234.7],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.72, 0.7],
                    speed_rpm=8787.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[3709.0, 4502.0, 4994.0, 5508.0, 5924.0],
                    polytropic_head_joule_per_kg=[135819.0, 129325.0, 121889.0, 110617.0, 98629.7],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.73, 0.7],
                    speed_rpm=9886.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[3928.0, 4507.0, 5002.0, 5499.0, 6249.0],
                    polytropic_head_joule_per_kg=[151417.0, 146983.0, 140773.0, 131071.0, 109705.0],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.74, 0.7],
                    speed_rpm=10435.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[4053.0, 4501.0, 4999.0, 5493.0, 6001.0, 6439.0],
                    polytropic_head_joule_per_kg=[161345.0, 157754.0, 152506.0, 143618.0, 131983.0, 117455.0],
                    efficiency_fraction=[0.72, 0.73, 0.74, 0.74, 0.72, 0.7],
                    speed_rpm=10767.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[4139.0, 5002.0, 5494.0, 6009.0, 6560.0],
                    polytropic_head_joule_per_kg=[167544.0, 159657.0, 151358.0, 139910.0, 121477.0],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.73, 0.7],
                    speed_rpm=10984.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[4328.0, 4999.0, 5506.0, 6028.0, 6507.0, 6908.0],
                    polytropic_head_joule_per_kg=[185232.0, 178885.0, 171988.0, 161766.0, 147512.0, 133602.0],
                    efficiency_fraction=[0.72, 0.74, 0.74, 0.74, 0.72, 0.7],
                    speed_rpm=11533.0,
                ),
            ]
        )
    )


def test_properties(variable_speed_chart):
    np.testing.assert_equal(variable_speed_chart.speed_values, [1, 2])
    assert variable_speed_chart.minimum_rate == 1.0
    assert variable_speed_chart.maximum_rate == 7.0
    assert variable_speed_chart.minimum_speed == 1
    assert variable_speed_chart.maximum_speed == 2

    assert variable_speed_chart.get_curve_by_speed(2) == variable_speed_chart.curves[1]
    assert variable_speed_chart.is_100_percent_efficient

    assert variable_speed_chart.minimum_speed_curve.rate == [1.0, 2.5, 5.5]
    assert variable_speed_chart.minimum_speed_curve.head == [4.5, 4.0, 2.5]
    assert variable_speed_chart.minimum_speed_curve.efficiency == [1, 1, 1]
    assert variable_speed_chart.minimum_speed_curve.speed_rpm == 1

    assert variable_speed_chart.maximum_speed_curve.rate == [3.0, 5.0, 7.0]
    assert variable_speed_chart.maximum_speed_curve.head == [7.5, 6.0, 5.0]
    assert variable_speed_chart.maximum_speed_curve.efficiency == [1, 1, 1]
    assert variable_speed_chart.maximum_speed_curve.speed_rpm == 2


def test_minimum_head_function():
    chart_curve_minimum_speed = ChartCurveDTO(
        rate_actual_m3_hour=[500, 1000, 2000, 3000],
        polytropic_head_joule_per_kg=[10, 20, 40, 60],
        efficiency_fraction=[1, 1, 1, 1],
        speed_rpm=10,
    )
    chart_curve_maximum_speed = ChartCurveDTO(
        rate_actual_m3_hour=[300, 4000, 5000, 6000],
        polytropic_head_joule_per_kg=[60, 80, 100, 120],
        efficiency_fraction=[1, 1, 1, 1],
        speed_rpm=100,
    )

    variable_speed_chart = VariableSpeedChart(
        VariableSpeedChartDTO(curves=[chart_curve_minimum_speed, chart_curve_maximum_speed])
    )

    # Testing that a low rate should give minimum head of 10 and a high rate should give maximum of 120.
    assert variable_speed_chart.minimum_head_as_function_of_rate(0) == 10
    assert variable_speed_chart.minimum_head_as_function_of_rate(1000000) == 120

    # Testing that the function works within min and max rate given in input
    assert variable_speed_chart.minimum_head_as_function_of_rate(500) == 10
    assert variable_speed_chart.minimum_head_as_function_of_rate(750) == 15
    assert variable_speed_chart.minimum_head_as_function_of_rate(2500) == 50
    assert variable_speed_chart.minimum_head_as_function_of_rate(3000) == 60


def test_minimum_head_function2(variable_speed_chart):
    np.testing.assert_allclose(
        variable_speed_chart.minimum_head_as_function_of_rate([-1.0, 1.0, 4.0, 5.5, 6.25, 9.0]),
        [4.5, 4.5, 3.25, 2.5, 3.75, 5.0],
    )


def test_minimum_head_function_with_ill_defined_curve():
    # "Ugly" chart where maximum speed maximum rate is above minimum speed curve
    chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[1.0, 2.5, 5.5],
                    polytropic_head_joule_per_kg=[4.5, 4.0, 2.5],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=1,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[3.0, 3.5, 4.0],
                    polytropic_head_joule_per_kg=[7.5, 6.0, 5.0],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=2,
                ),
            ]
        )
    )
    np.testing.assert_allclose(
        chart.minimum_head_as_function_of_rate([-1.0, 1.0, 4.0, 5.5, 6.25, 9.0]),
        [4.5, 4.5, 3.25, 2.5, 2.5, 2.5],
    )


def test_max_flow_head_functions():
    chart_curve_minimum_speed = ChartCurveDTO(
        rate_actual_m3_hour=[1000, 2000, 3000, 5000],
        polytropic_head_joule_per_kg=[5, 10, 15, 20],
        efficiency_fraction=[1, 1, 1, 1],
        speed_rpm=10,
    )
    chart_curve_maximum_speed = ChartCurveDTO(
        rate_actual_m3_hour=[1000, 2000, 3000, 5000],
        polytropic_head_joule_per_kg=[5, 10, 15, 20],
        efficiency_fraction=[1, 1, 1, 1],
        speed_rpm=100,
    )

    variable_speed_chart = VariableSpeedChart(
        VariableSpeedChartDTO(curves=[chart_curve_minimum_speed, chart_curve_maximum_speed])
    )

    assert variable_speed_chart.maximum_head_as_function_of_rate(0) == 5
    assert variable_speed_chart.maximum_head_as_function_of_rate(1000) == 5
    assert variable_speed_chart.maximum_head_as_function_of_rate(2500) == 12.5
    assert variable_speed_chart.maximum_head_as_function_of_rate(5000) == 20
    assert variable_speed_chart.maximum_head_as_function_of_rate(10000) == 20

    # assert max_flow_func(0) == 1000
    assert variable_speed_chart.maximum_rate_as_function_of_head(5) == 1000
    assert variable_speed_chart.maximum_rate_as_function_of_head(12.5) == 2500
    assert variable_speed_chart.maximum_rate_as_function_of_head(20) == 5000
    # assert max_flow_func(30) == 5000


def test_get_efficiency_variable_chart():
    chart_curve_1 = ChartCurveDTO(
        rate_actual_m3_hour=[1, 3, 5],
        polytropic_head_joule_per_kg=[3, 2, 1],
        efficiency_fraction=[0.10, 0.20, 0.30],
        speed_rpm=1,
    )
    chart_curve_2 = ChartCurveDTO(
        rate_actual_m3_hour=[1.5, 5.5],
        polytropic_head_joule_per_kg=[4, 2],
        efficiency_fraction=[0.40, 0.50],
        speed_rpm=2,
    )
    chart_curve_3 = ChartCurveDTO(
        rate_actual_m3_hour=[2, 5, 6],
        polytropic_head_joule_per_kg=[5, 4, 3],
        efficiency_fraction=[0.60, 0.70, 0.80],
        speed_rpm=3,
    )

    variable_speed_chart = VariableSpeedChart(
        VariableSpeedChartDTO(curves=[chart_curve_1, chart_curve_2, chart_curve_3])
    )

    # Check values at points defined in chart
    efficiencies = variable_speed_chart.efficiency_as_function_of_rate_and_head(
        rates=np.asarray([1, 3, 5, 1.5, 5.5, 2, 5, 6]),
        heads=np.asarray([3, 2, 1, 4, 2, 5, 4, 3]),
    )
    np.testing.assert_equal(efficiencies, [(i + 1) / 10 for i in range(8)])

    # Check values at chart curve, but not at points
    efficiencies = variable_speed_chart.efficiency_as_function_of_rate_and_head(
        rates=np.asarray([2, 3.5, 5.5]),
        heads=np.asarray([2.5, 3, 3.5]),
    )
    np.testing.assert_almost_equal(efficiencies, [0.15, 0.45, 0.75])

    # Check for points between chart curves
    efficiencies = variable_speed_chart.efficiency_as_function_of_rate_and_head(
        rates=np.asarray([2.25]),
        heads=np.asarray([3]),
    )
    np.testing.assert_almost_equal(efficiencies, 0.2849502)

    # Check for points below and above
    efficiencies = variable_speed_chart.efficiency_as_function_of_rate_and_head(
        rates=np.asarray([2, 4]),
        heads=np.asarray([1, 5]),
    )
    np.testing.assert_almost_equal(efficiencies, [0.2044776, 0.6531856])

    # Check for points left and right
    efficiencies = variable_speed_chart.efficiency_as_function_of_rate_and_head(
        rates=np.asarray([1, 5.5, 7]),
        heads=np.asarray([4, 1.5, 2]),
    )
    np.testing.assert_almost_equal(efficiencies, [0.3253873, 0.4079482, 0.4251169])


def test_efficiency_as_function_of_rate_and_head_zero_chart_data():
    """Edge case when we create a chart based on generic from input where the design points are rate=0, head=0 and
    a given efficiency such as 95%. For robustness and defencive programming we allow this to happen when asking
    for efficiency interpolation.
    """
    chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    polytropic_head_joule_per_kg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    efficiency_fraction=[0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95],
                    speed_rpm=75.0,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    polytropic_head_joule_per_kg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    efficiency_fraction=[0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95],
                    speed_rpm=105.0,
                ),
            ]
        )
    )

    efficiencies = chart.efficiency_as_function_of_rate_and_head(rates=np.array([1, 2, 3]), heads=np.array([3, 2, 1]))

    assert efficiencies.tolist() == [0.95, 0.95, 0.95]


def test_min_flow_function():
    chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[1.0, 2.0],
                    polytropic_head_joule_per_kg=[1.0, 0.5],
                    efficiency_fraction=[1, 1],
                    speed_rpm=1,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[2.0, 3.5],
                    polytropic_head_joule_per_kg=[3.0, 2.0],
                    efficiency_fraction=[1, 1],
                    speed_rpm=2,
                ),
            ]
        )
    )

    # With choking
    # Interior point
    assert chart.minimum_rate_as_function_of_head(2.0) == 1.5
    # End points
    assert chart.minimum_rate_as_function_of_head(1.0) == 1.0
    assert chart.minimum_rate_as_function_of_head(3.0) == 2.0
    # Extrapolated points
    assert chart.minimum_rate_as_function_of_head(-0.2) == 1.0
    assert chart.minimum_rate_as_function_of_head(3000.0) == 2.0

    # Without choking
    # Interior point
    assert chart.minimum_rate_as_function_of_head_no_choking(2.0) == 1.5
    # End points
    assert chart.minimum_rate_as_function_of_head_no_choking(1.0) == 1.0
    assert chart.minimum_rate_as_function_of_head_no_choking(3.0) == 2.0
    # Extrapolated points
    assert chart.minimum_rate_as_function_of_head_no_choking(-0.2) == 2.0
    assert chart.minimum_rate_as_function_of_head_no_choking(3000.0) == 2.0


def test_speed_curve_sorting():
    # (rate, head) - points. On purpose, the points are not ordered
    chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[0.5, 2.0, 4.0],
                    polytropic_head_joule_per_kg=[3.0, 2.0, 1.0],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=1,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[1.0, 2.5, 5.5],
                    polytropic_head_joule_per_kg=[4.5, 4.0, 2.5],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=2,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[0.75, 2.25, 4.75],
                    polytropic_head_joule_per_kg=[3.75, 3.0, 1.75],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=1.5,
                ),
            ]
        )
    )

    assert chart.speed_values == [1, 1.5, 2]


def test_maximum_flow_function():
    # (rate, head) - points. On purpose, the points are not ordered
    chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[0.5, 2.0, 4.0],
                    polytropic_head_joule_per_kg=[3.0, 2.0, 1.0],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=1,
                ),
                ChartCurveDTO(
                    rate_actual_m3_hour=[1.0, 2.5, 5.5],
                    polytropic_head_joule_per_kg=[4.5, 4.0, 2.5],
                    efficiency_fraction=[1, 1, 1],
                    speed_rpm=2,
                ),
            ]
        )
    )

    # With choking - meaning points under stone wall may be "lifted up to chart", hence only maximum speed points
    # define maximum flow function
    # Without choking - points under stone wall are invalid and the maximum rate for head values below maximum speed's
    # minimum head are defined by stone wall

    # Points within range of maximum speed + point above maximum speed, both with and without choking
    np.testing.assert_equal(
        chart.maximum_rate_as_function_of_head_no_choking([2.5, 4.5, 3.25, 5.0]), [5.5, 1.0, 4.0, 1.0]
    )
    np.testing.assert_equal(chart.maximum_rate_as_function_of_head([2.5, 4.5, 3.25, 5.0]), [5.5, 1.0, 4.0, 1.0])

    # Points below maximum speed. Will differ dependent on choking
    np.testing.assert_equal(chart.maximum_rate_as_function_of_head([1.0, 1.75]), 5.5)
    np.testing.assert_equal(chart.maximum_rate_as_function_of_head_no_choking([1.0, 1.75]), [4.0, 4.75])


def test_is_100_percent_efficient(variable_speed_chart):
    assert variable_speed_chart.is_100_percent_efficient

    efficient_chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[1, 2],
                    polytropic_head_joule_per_kg=[1, 2],
                    efficiency_fraction=[0.5, 0.5],
                    speed_rpm=1,
                )
            ]
            * 2
        )
    )
    assert not efficient_chart.is_100_percent_efficient


def test_find_closest_speeds(variable_speed_chart_multiple_speeds):
    # Requested speed is internal
    speed = 9336
    curve_above = variable_speed_chart_multiple_speeds.closest_curve_above_speed(speed)
    curve_below = variable_speed_chart_multiple_speeds.closest_curve_below_speed(speed)

    assert curve_above.speed_rpm == 9886
    assert curve_below.speed_rpm == 8787

    # Requested speed exists in given data
    speed = 9886
    curve_above = variable_speed_chart_multiple_speeds.closest_curve_above_speed(speed)
    curve_below = variable_speed_chart_multiple_speeds.closest_curve_below_speed(speed)

    assert curve_above.speed_rpm == speed
    assert curve_below.speed_rpm == speed

    # Requested speed is smaller than smallest given in data
    speed = 1
    curve_above = variable_speed_chart_multiple_speeds.closest_curve_above_speed(speed)
    curve_below = variable_speed_chart_multiple_speeds.closest_curve_below_speed(speed)

    assert curve_above.speed_rpm == 7689
    assert curve_below is None

    # Requested speed is larger than largest given in data
    speed = 12000
    curve_above = variable_speed_chart_multiple_speeds.closest_curve_above_speed(speed)
    curve_below = variable_speed_chart_multiple_speeds.closest_curve_below_speed(speed)

    assert curve_above is None
    assert curve_below.speed_rpm == 11533


def test_setup_minimum_and_maximum_rate_as_functions_of_speed(
    variable_speed_chart,
):
    np.testing.assert_equal(variable_speed_chart.minimum_rate_as_function_of_speed.x, [1.0, 2.0])
    np.testing.assert_equal(variable_speed_chart.minimum_rate_as_function_of_speed.y, [1.0, 3.0])
    np.testing.assert_equal(variable_speed_chart.maximum_rate_as_function_of_speed.x, [1.0, 2.0])
    np.testing.assert_equal(variable_speed_chart.maximum_rate_as_function_of_speed.y, [5.5, 7.0])

    np.testing.assert_almost_equal(
        variable_speed_chart.minimum_rate_as_function_of_speed([0, 1, 1.1, 1.5, 1.9, 2, 3]),
        [1.0, 1.0, 1.2, 2.0, 2.8, 3.0, 3.0],
    )
    np.testing.assert_almost_equal(
        variable_speed_chart.maximum_rate_as_function_of_speed([0, 1, 1.1, 1.5, 1.9, 2, 3]),
        [5.5, 5.5, 5.65, 6.25, 6.85, 7.0, 7.0],
    )
