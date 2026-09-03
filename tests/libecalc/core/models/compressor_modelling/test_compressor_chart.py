import numpy as np
import pytest
from pytest import approx

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart


@pytest.fixture
def variable_speed_compressor_chart(variable_speed_compressor_chart_data) -> CompressorChart:
    """Convert DTO to domain object."""
    return CompressorChart(variable_speed_compressor_chart_data)


@pytest.fixture
def predefined_variable_speed_compressor_chart_2(
    chart_curve_factory, compressor_chart_factory, chart_data_factory
) -> CompressorChart:
    chart_data = {
        1300: {
            "rate": [159, 153, 143, 132, 122, 112, 102, 92, 81, 71, 67],
            "head": [850, 906, 992, 1082, 1162, 1234, 1286, 1336, 1366, 1387, 1394],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.769, 0.752, 0.730, 0.721],
        },
        1200: {
            "rate": [152, 145, 136, 126, 116, 107, 97, 87, 78, 68, 64, 143],
            "head": [771, 821, 900, 982, 1054, 1120, 1166, 1212, 1239, 1258, 1265, 682],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.769, 0.752, 0.730, 0.721, 0.700],
        },
        1100: {
            "rate": [143, 137, 128, 119, 109, 100, 91, 89, 82, 73, 64, 60],
            "head": [682, 727, 796, 869, 933, 991, 1032, 1041, 1072, 1097, 1113, 1119],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.772, 0.769, 0.752, 0.730, 0.721],
        },
        1000: {
            "rate": [137, 131, 122, 113, 105, 96, 87, 79, 70, 61, 58],
            "head": [625, 665, 729, 795, 854, 907, 945, 981, 1004, 1019, 1024],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.769, 0.752, 0.730, 0.721],
        },
        900: {
            "rate": [121, 116, 109, 101, 93, 85, 78, 70, 62, 54, 51],
            "head": [494, 526, 576, 628, 674, 716, 746, 775, 793, 805, 810],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.769, 0.752, 0.730, 0.721],
        },
        800: {
            "rate": [106, 102, 95, 88, 81, 75, 68, 61, 54, 48, 45],
            "head": [378, 403, 441, 481, 516, 549, 572, 594, 607, 616, 620],
            "efficiency": [0.700, 0.715, 0.738, 0.761, 0.772, 0.776, 0.773, 0.769, 0.752, 0.730, 0.721],
        },
    }
    chart_curves = [
        chart_curve_factory(
            rate_actual_m3_hour=values["rate"],
            polytropic_head_joule_per_kg=values["head"],
            efficiency_fraction=values["efficiency"],
            speed_rpm=speed,
        )
        for speed, values in chart_data.items()
    ]

    return compressor_chart_factory(chart_data_factory.from_curves(curves=chart_curves))


class TestPolytropicHeadAndEfficiencyCalculation:
    def test_calculate_polytropic_head_and_efficiency_single_point_speed_given(self, variable_speed_compressor_chart):
        # Test for speed present in chart data, between two rates, expect average as this is linear interpolation
        speed = 9886
        rate = (3709.0 + 4502.0) / 2
        expected_head = (135819.0 + 129325.0) / 2
        expected_efficiency = (0.72 + 0.74) / 2
        expected_chart_area_flag = ChartAreaFlag.INTERNAL_POINT
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=speed,
            actual_rate_m3_per_hour=rate,
        )
        assert result.polytropic_head == approx(expected_head)
        assert result.polytropic_efficiency == approx(expected_efficiency)
        assert result.chart_area_flag == expected_chart_area_flag

    def test_calculate_polytropic_head_and_efficiency_single_point_internal_point_speed_interpolation(
        self, variable_speed_compressor_chart
    ):
        # Test for internal point, but where speed is not present in input data, i.e. between two defined speed values
        speed = (9886.0 + 8787) / 2
        rate = (5924.0 + 3709.0 + 3306.0 + 5242.0) / 4.0
        rate_for_speed_below = 4274.0  # (3306.0+5242.0) / 2
        rate_for_speed_above = 4816.5  # (5924.0+3709.0)/ 2
        head_for_speed_below = _linear_scale_helper(
            x=rate_for_speed_below,
            x1=4000.0,
            y1=101955.0,
            x2=4499.0,
            y2=95225.60,
        )
        head_for_speed_above = _linear_scale_helper(
            x=rate_for_speed_above,
            x1=4502.0,
            y1=129325.0,
            x2=4994.0,
            y2=121889.0,
        )
        efficiency_for_speed_below = 0.74
        efficiency_for_speed_above = 0.74
        expected_head = (head_for_speed_below + head_for_speed_above) / 2
        expected_efficiency = (efficiency_for_speed_below + efficiency_for_speed_above) / 2.0
        expected_chart_area_flag = ChartAreaFlag.INTERNAL_POINT
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=speed,
            actual_rate_m3_per_hour=rate,
        )
        assert result.polytropic_head == approx(expected_head)
        assert result.polytropic_efficiency == approx(expected_efficiency)
        assert result.chart_area_flag == expected_chart_area_flag

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_too_large(
        self, variable_speed_compressor_chart
    ):
        # Test for point with too large speed
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=12000,
            actual_rate_m3_per_hour=5000,
        )
        assert np.isnan(result.polytropic_head)
        assert np.isnan(result.polytropic_efficiency)
        assert result.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_SPEED

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_too_large_rate_too_large(
        self, variable_speed_compressor_chart
    ):
        # Too large speed, but also too large rate. Still Chart area flag reflects the large speed
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=12000,
            actual_rate_m3_per_hour=5000000,
        )
        assert np.isnan(result.polytropic_head)
        assert np.isnan(result.polytropic_efficiency)
        assert result.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_SPEED

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_too_large_rate_below_minimum(
        self, variable_speed_compressor_chart
    ):
        # Too large speed, but also too small rate. Still Chart area flag reflects the large speed
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=12000,
            actual_rate_m3_per_hour=5,
        )
        assert np.isnan(result.polytropic_head)
        assert np.isnan(result.polytropic_efficiency)
        assert result.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_SPEED

    def test_calculate_polytropic_head_and_efficiency_single_point_rate_too_large(
        self, variable_speed_compressor_chart
    ):
        # Speed contained in input data, rate above maximum
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=10984,
            actual_rate_m3_per_hour=5000000000,
        )
        assert not result.is_valid
        assert (
            result.polytropic_head
            == variable_speed_compressor_chart.head_as_function_of_speed_for_rates_above_maximum_extrapolation(10984)
        )
        assert (
            result.polytropic_efficiency
            == variable_speed_compressor_chart.efficiency_as_function_of_speed_for_rates_above_maximum_extrapolation(
                10984
            )
        )
        assert result.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    def test_calculate_polytropic_head_and_efficiency_single_point_rate_below_minflow_speed_in_data(
        self, variable_speed_compressor_chart
    ):
        # Speed contained in input data, rate below minimum
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=10984,
            actual_rate_m3_per_hour=5,
        )
        assert result.polytropic_head == 167544.0
        assert result.polytropic_efficiency == 0.72
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE

    def test_calculate_polytropic_head_and_efficiency_single_point_rate_below_minflow(
        self, variable_speed_compressor_chart
    ):
        # Speed internal but not contained in input, rate below minimum
        speed = (9886.0 + 8787) / 2
        expected_head = (135819.0 + 107429.0) / 2
        expected_efficiency = 0.72
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=speed,
            actual_rate_m3_per_hour=5,
        )
        assert result.polytropic_head == expected_head
        assert result.polytropic_efficiency == expected_efficiency
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_below_minimum(
        self, variable_speed_compressor_chart
    ):
        # Speed below minimum speed
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=5,
            actual_rate_m3_per_hour=5000,
        )
        assert not result.is_valid
        assert np.isnan(result.polytropic_head)
        assert np.isnan(result.polytropic_efficiency)
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_SPEED

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_increased(
        self, variable_speed_compressor_chart
    ):
        # Accept speed increase - extrapolation
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=5,
            actual_rate_m3_per_hour=3504.0,
            increase_speed_below_assuming_choke=True,
        )
        assert result.polytropic_head == 78440.70
        assert result.polytropic_efficiency == 0.74
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_SPEED
        assert result.is_valid

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_increased_rate_too_large(
        self, variable_speed_compressor_chart
    ):
        # Accept speed increase - extrapolation, rate too large
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=5,
            actual_rate_m3_per_hour=50000.0,
            increase_speed_below_assuming_choke=True,
        )
        assert not result.is_valid
        assert (
            result.polytropic_head
            == variable_speed_compressor_chart.head_as_function_of_speed_for_rates_above_maximum_extrapolation(5)
        )
        assert (
            result.polytropic_efficiency
            == variable_speed_compressor_chart.efficiency_as_function_of_speed_for_rates_above_maximum_extrapolation(5)
        )
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE

    def test_calculate_polytropic_head_and_efficiency_single_point_speed_increased_rate_increased(
        self, variable_speed_compressor_chart
    ):
        # Accept speed increase - extrapolation, rate smaller than minimum
        result = variable_speed_compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=5,
            actual_rate_m3_per_hour=1.0,
            increase_speed_below_assuming_choke=True,
        )
        assert result.polytropic_head == 82531.50
        assert result.polytropic_efficiency == 0.72
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE
        assert result.is_valid


def _linear_scale_helper(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    return y1 + (y2 - y1) / (x2 - x1) * (x - x1)


def test_calculate_head_and_efficiency_for_internal_point_between_given_speeds(variable_speed_compressor_chart, caplog):
    test_speeds = 3 * [7689.0] + 3 * [8500] + 3 * [10767]
    test_rates = [2900.0, 3500, 4595.0] + [3600.0, 4000.0, 5000.0] + [4053.0, 5000.0, 6439.0]

    expected_results = (
        [(82531.50, 0.72), (78467.79139072847, 0.7398675496688741), (60105.80, 0.70)]
        + [(97870.68534708404, 0.7319373178043224), (94093.65102740255, 0.74), (75228.64110476857, 0.705707255697281)]
        + [(161345.0, 0.72), (152488.008097166, 0.74), (117455.0, 0.70)]
    )
    for speed, rate, expected_result in zip(test_speeds, test_rates, expected_results):
        result = variable_speed_compressor_chart.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
            speed=speed, rate=rate
        )
        assert result[0] == approx(expected_result[0])
        assert result[1] == approx(expected_result[1])

    # Test some points which are not internal
    caplog.set_level("CRITICAL")
    with pytest.raises(IllegalStateException):
        variable_speed_compressor_chart.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
            speed=5000, rate=5000
        )
    with pytest.raises(IllegalStateException):
        variable_speed_compressor_chart.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
            speed=8000, rate=10000
        )


def test_calculate_scaling_factors_for_speed_below_and_above():
    assert CompressorChart._calculate_scaling_factors_for_speed_below_and_above(
        speed=9336.5,
        speed_above=9886,
        speed_below=8787.0,
    ) == (0.5, 0.5)


def test_single_speed_compressor_chart_control_margin(
    chart_curve_factory, compressor_chart_factory, chart_data_factory
):
    """When adjusting the chart using a control margin, we multiply the average of the minimum rate for all curves
    by the control margin factor and multiply by the margin:

    Here:
        minimum rates are [1, 4] => average = 2
        control margin = 0.1 (10 %)
        Result: 2 *  0.1 = 0.25

    This is used to move each minimum rate to the "right" by 0.25.

    :return:
    """
    control_margin = 0.1
    curve = chart_curve_factory(
        speed_rpm=1,
        rate_actual_m3_hour=[1, 2, 3],
        polytropic_head_joule_per_kg=[4, 5, 6],
        efficiency_fraction=[0.7, 0.8, 0.9],
    )

    compressor_chart = chart_data_factory.from_curves(
        curves=[curve],
        control_margin=control_margin,
    )

    adjust_minimum_rate_by = (curve.rate_actual_m3_hour[-1] - curve.rate_actual_m3_hour[0]) * control_margin

    new_minimum_rate = curve.rate_actual_m3_hour[0] + adjust_minimum_rate_by

    assert compressor_chart.get_adjusted_curves()[0].minimum_rate == new_minimum_rate


def test_variable_speed_compressor_chart_control_margin(
    chart_curve_factory, compressor_chart_factory, chart_data_factory
):
    """When adjusting the chart using a control margin, we multiply the average of the minimum rate for all curves
    by the control margin factor and multiply by the margin:

    Here:
        minimum rates are [1, 4] => average = 2
        control margin = 0.1 (10 %)
        Result: 2 *  0.1 = 0.25

    This is used to move eash minimum rate to the "right" by 0.25.

    :return:
    """
    curve_1 = chart_curve_factory(
        speed_rpm=1,
        rate_actual_m3_hour=[1, 2, 3],
        polytropic_head_joule_per_kg=[4, 5, 6],
        efficiency_fraction=[0.7, 0.8, 0.9],
    )
    curve_2 = chart_curve_factory(
        speed_rpm=1,
        rate_actual_m3_hour=[4, 5, 6],
        polytropic_head_joule_per_kg=[7, 8, 9],
        efficiency_fraction=[0.101, 0.82, 0.9],
    )
    control_margin = 0.1
    compressor_chart = chart_data_factory.from_curves(
        curves=[
            curve_1,
            curve_2,
        ],
        control_margin=control_margin,
    )

    adjust_minimum_rate_by_speed1 = (curve_1.rate_actual_m3_hour[-1] - curve_1.rate_actual_m3_hour[0]) * control_margin
    adjust_minimum_rate_by_speed2 = (curve_2.rate_actual_m3_hour[-1] - curve_2.rate_actual_m3_hour[0]) * control_margin

    new_minimum_rate_speed1 = curve_1.rate_actual_m3_hour[0] + adjust_minimum_rate_by_speed1
    new_minimum_rate_speed2 = curve_2.rate_actual_m3_hour[0] + adjust_minimum_rate_by_speed2

    assert compressor_chart.get_adjusted_curves()[0].rate_actual_m3_hour[0] == new_minimum_rate_speed1
    assert compressor_chart.get_adjusted_curves()[1].rate_actual_m3_hour[0] == new_minimum_rate_speed2


def test_compare_variable_speed_compressor_chart_head_and_efficiency_known_point_compared_to_interpolation(
    predefined_variable_speed_compressor_chart_2,
):
    known_speed_1 = 1100
    known_rate_1 = 109
    result_known_case_1 = (
        predefined_variable_speed_compressor_chart_2.calculate_polytropic_head_and_efficiency_single_point(
            speed=known_speed_1, actual_rate_m3_per_hour=known_rate_1
        )
    )

    # Lookup against known value that is in the input data should yield no uncertainty
    assert result_known_case_1.polytropic_efficiency == 0.772
    assert result_known_case_1.polytropic_head == 933

    known_speed_2 = 1000
    known_rate_2 = 105
    result_known_case_2 = (
        predefined_variable_speed_compressor_chart_2.calculate_polytropic_head_and_efficiency_single_point(
            speed=known_speed_2, actual_rate_m3_per_hour=known_rate_2
        )
    )

    # Lookup against known value that is in the input data should yield no uncertainty
    assert result_known_case_2.polytropic_efficiency == 0.772
    assert result_known_case_2.polytropic_head == 854

    result_speed_close_above_case_1 = (
        predefined_variable_speed_compressor_chart_2.calculate_polytropic_head_and_efficiency_single_point(
            speed=1110, actual_rate_m3_per_hour=known_rate_1
        )
    )

    result_speed_close_below_case_2 = (
        predefined_variable_speed_compressor_chart_2.calculate_polytropic_head_and_efficiency_single_point(
            speed=990, actual_rate_m3_per_hour=known_rate_2
        )
    )

    """
    Efficiency should be quite close the the reference cases, but not exactly the same.
    """
    assert result_speed_close_above_case_1.polytropic_efficiency == pytest.approx(
        result_known_case_1.polytropic_efficiency, rel=0.005
    )
    assert result_speed_close_below_case_2.polytropic_efficiency == pytest.approx(
        result_known_case_2.polytropic_efficiency, rel=0.005
    )

    """
    Some bigger differences in polytropic head because the two speed curves at
    the same rate has significantly different head values.
    """
    assert result_speed_close_above_case_1.polytropic_head == pytest.approx(
        result_known_case_1.polytropic_head, rel=0.05
    )
    assert result_speed_close_below_case_2.polytropic_head == pytest.approx(
        result_known_case_2.polytropic_head, rel=0.05
    )
