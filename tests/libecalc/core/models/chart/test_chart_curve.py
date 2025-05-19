import numpy as np
import pytest

from libecalc.common.serializable_chart import ChartCurveDTO
from libecalc.domain.process.chart import ChartCurve


@pytest.fixture
def chart_curve() -> ChartCurve:
    return ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[1, 2, 3, 4, 5],
            polytropic_head_joule_per_kg=[5, 4, 3, 2, 1],
            efficiency_fraction=[0.5, 0.6, 0.7, 0.6, 0.5],
            speed_rpm=1,
        )
    )


@pytest.fixture
def chart_curve_unordered() -> ChartCurve:
    return ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[2, 3, 4, 5, 1],
            polytropic_head_joule_per_kg=[4, 3, 2, 1, 5],
            efficiency_fraction=[0.6, 0.7, 0.6, 0.5, 0.5],
            speed_rpm=1,
        )
    )


def test_chart_curve_data_setup_from_arrays(chart_curve):
    assert np.array_equal(chart_curve.rate_values, [1, 2, 3, 4, 5])
    assert np.array_equal(chart_curve.head_values, [5, 4, 3, 2, 1])
    assert np.array_equal(chart_curve.efficiency_values, [0.5, 0.6, 0.7, 0.6, 0.5])

    assert chart_curve.rate_actual_m3_hour[0] == 1.0
    assert chart_curve.rate_actual_m3_hour[1] == 2.0
    assert chart_curve.polytropic_head_joule_per_kg[0] == 5.0
    assert chart_curve.polytropic_head_joule_per_kg[1] == 4.0
    assert chart_curve.efficiency_fraction[0] == 0.5
    assert chart_curve.efficiency_fraction[1] == 0.6

    assert chart_curve.maximum_rate == 5
    assert chart_curve.minimum_rate == 1
    assert not chart_curve.is_100_percent_efficient


def test_chart_curve_data_add_valid_and_invalid_curve_data_point(chart_curve, chart_curve_unordered):
    assert np.array_equal(chart_curve.rate_values, chart_curve_unordered.rate_values)
    assert np.array_equal(chart_curve.head_values, chart_curve_unordered.head_values)
    assert np.array_equal(chart_curve.efficiency_values, chart_curve_unordered.efficiency_values)


def test_chart_curve_100_percent_efficient():
    chart_curve_100_percent_efficient = ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[1, 2], polytropic_head_joule_per_kg=[2, 1], efficiency_fraction=[1, 1], speed_rpm=1
        )
    )
    assert chart_curve_100_percent_efficient.is_100_percent_efficient


def test_chart_curve_data_invalid_setup_from_arrays(caplog):
    # Efficiency is a fraction between 0 and 1. Where 0 is 0 % efficiency and 1 is 100 % efficiency.
    caplog.set_level("CRITICAL")
    with pytest.raises(ValueError):
        ChartCurve(
            ChartCurveDTO(
                rate_actual_m3_hour=[1, 2.0],
                polytropic_head_joule_per_kg=[3, 4.0],
                efficiency_fraction=[30.0, 70.0],
                speed_rpm=1,
            )
        )

    # Chart curve should have at least two points
    with pytest.raises(ValueError) as ve:
        ChartCurve(
            ChartCurveDTO(
                rate_actual_m3_hour=[1],
                polytropic_head_joule_per_kg=[3],
                efficiency_fraction=[0.3],
                speed_rpm=1,
            )
        )
        assert "A chart curve can not be defined by a single point." in str(ve.value)


def test_chart_curve_sort_input_values():
    """Values should be sorted by the root validator in pydantic."""
    curve = ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[3, 2, 4, 1],
            polytropic_head_joule_per_kg=[1, 2, 3, 4],
            efficiency_fraction=[1, 1, 1, 1],
            speed_rpm=1,
        )
    )

    assert curve.rate_actual_m3_hour == [1, 2, 3, 4]
    assert curve.polytropic_head_joule_per_kg == [4, 2, 1, 3]


def test_efficiency_as_function_of_rate(chart_curve):
    np.testing.assert_almost_equal(
        chart_curve.efficiency_as_function_of_rate([0, 1, 1.5, 2.5, 5, 6]), [0.5, 0.5, 0.55, 0.65, 0.5, 0.5]
    )


def test_head_as_function_of_rate(chart_curve):
    _ = ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[1, 2, 3, 4, 5],
            polytropic_head_joule_per_kg=[5, 4, 3, 2, 1],
            efficiency_fraction=[0.5, 0.6, 0.7, 0.6, 0.5],
            speed_rpm=1,
        )
    )

    np.testing.assert_almost_equal(
        chart_curve.head_as_function_of_rate([0, 1, 2.5, 3, 5, 6]), [5.0, 5.0, 3.5, 3.0, 1.0, 1.0]
    )


def test_maximum_rate_as_function_of_head(chart_curve):
    np.testing.assert_almost_equal(
        chart_curve.rate_as_function_of_head([0, 1, 1.5, 2.5, 5, 6]), [5.0, 5.0, 4.5, 3.5, 1.0, 1.0]
    )


def test_maximum_head_as_function_of_rate(chart_curve):
    np.testing.assert_almost_equal(
        chart_curve.head_as_function_of_rate([0, 1, 1.5, 2.5, 5, 6]), [5.0, 5.0, 4.5, 3.5, 1.0, 1.0]
    )


def test_rate_head_and_efficiency_at_minimum_rate(chart_curve):
    np.testing.assert_almost_equal(chart_curve.rate_head_and_efficiency_at_minimum_rate, (1.0, 5.0, 0.5))


def test_rate_head_and_efficiency_at_maximum_rate(chart_curve):
    np.testing.assert_almost_equal(chart_curve.rate_head_and_efficiency_at_maximum_rate, (5.0, 1.0, 0.5))


def test_distance_efficiency():
    """Integration test."""
    chart_curve = ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[577, 336, 708, 842, 824, 826, 825, 1028],
            polytropic_head_joule_per_kg=[1718.7, 1778.7, 1665.2, 1587.8, 1601.9, 1601.9, 1602.7, 1460.6],
            efficiency_fraction=[0.6203, 0.4717, 0.6683, 0.6996, 0.695, 0.6975, 0.6981, 0.7193],
            speed_rpm=1,
        )
    )

    # Point within rate range of curve
    distance, efficiency = chart_curve.get_distance_and_efficiency_from_closest_point_on_curve(400, 1600)
    assert distance == pytest.approx(157.94506867462806)
    assert efficiency == pytest.approx(0.5346901525591349)

    # Point with rate less than min rate in curve
    distance, efficiency = chart_curve.get_distance_and_efficiency_from_closest_point_on_curve(100, 1600)
    assert distance == pytest.approx(296.0231240967503)
    assert efficiency == pytest.approx(0.4717)  # Equal to min rate eff


def test_interpolation_functions():
    """Integration test."""
    # NB: Minimum rate not first, will be sorted
    # Random order of input columns
    chart_curve = ChartCurve(
        ChartCurveDTO(
            rate_actual_m3_hour=[577, 336, 708, 842, 824, 826, 825, 1028],
            polytropic_head_joule_per_kg=[1718.7, 1778.7, 1665.2, 1587.8, 1601.9, 1601.9, 1602.7, 1460.6],
            efficiency_fraction=[0.6203, 0.4717, 0.6683, 0.6996, 0.695, 0.6975, 0.6981, 0.7193],
            speed_rpm=1,
        )
    )
    assert not (np.asarray(chart_curve.rate_head_and_efficiency_at_minimum_rate) - [336.0, 1778.7, 0.4717]).any()
    assert not (np.asarray(chart_curve.rate_head_and_efficiency_at_maximum_rate) - [1028, 1460.6, 0.7193]).any()
    assert chart_curve.efficiency_as_function_of_rate(708) == 0.6683
    assert np.round(chart_curve.efficiency_as_function_of_rate(456.5), 3) == 0.546
    assert chart_curve.get_distance_and_efficiency_from_closest_point_on_curve(577, 1718.7) == (0.0, 0.6203)
    np.testing.assert_approx_equal(
        chart_curve.get_distance_and_efficiency_from_closest_point_on_curve(400, 1600)[0], 157.9450
    )

    np.testing.assert_almost_equal(chart_curve.rate_head_and_efficiency_at_minimum_rate, [336, 1778.7, 0.4717])
    np.testing.assert_almost_equal(chart_curve.rate_head_and_efficiency_at_maximum_rate, [1028, 1460.6, 0.7193])
    assert chart_curve.efficiency_as_function_of_rate(600) == pytest.approx(0.6287274809160306)

    assert chart_curve.efficiency_as_function_of_rate(300) == pytest.approx(0.4717)
    assert chart_curve.efficiency_as_function_of_rate(1100) == pytest.approx(0.7193)
    assert chart_curve.head_as_function_of_rate(600) == pytest.approx(1709.3068702290077)
    assert chart_curve.head_as_function_of_rate(300) == pytest.approx(1778.7)
    assert chart_curve.head_as_function_of_rate(1100) == pytest.approx(1460.6)
