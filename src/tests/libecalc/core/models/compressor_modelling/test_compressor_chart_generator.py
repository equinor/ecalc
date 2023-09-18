import numpy as np
import pytest
from libecalc.core.models.compressor.train.chart.chart_creator import (
    CompressorChartCreator,
)
from libecalc.core.models.compressor.train.chart.variable_speed_compressor_chart import (
    VariableSpeedCompressorChart,
)


@pytest.fixture
def generic_compressor_chart() -> VariableSpeedCompressorChart:
    """The generic compressor chart from design point is just a scaling of a pre-defined generic compressor chart.
    The generator will return a Variable Speed Compressor Chart.
    """
    return CompressorChartCreator.from_rate_and_head_design_point(
        design_actual_rate_m3_per_hour=4000.0,
        design_head_joule_per_kg=100000.0,
        polytropic_efficiency=0.8,
    )


def test_compressor_chart_generic_internal_points(generic_compressor_chart):
    """Test maximum rate with and without choking/extrapolation below stone wall
    First the end points and internal point in maximum speed curve
    Then points above and below maximum speed curve
    For test without choking, also end point, internal point and point below stone wall
    With choking, i.e. head values below stone wall are lifted.
    """
    result = generic_compressor_chart.get_maximum_rate(
        heads=np.asarray([0.99827269, 1.289869247, 0.809949924, 0.5, 2.0]) * 100000.0,
        extrapolate_heads_below_minimum=True,
    )
    np.testing.assert_allclose(
        result,
        np.asarray([1.231463064, 0.878913798, 1.323778851, 1.323778851, 0.878913798]) * 4000.0,
    )


def test_compressor_chart_generic_below_stone_wall(generic_compressor_chart):
    """Without choking, head values below stone wall are infeasible."""
    result = generic_compressor_chart.get_maximum_rate(
        heads=np.asarray([0.99827269, 1.289869247, 0.809949924, 0.6094772945, 2.0, 0.409004665, 0.2]) * 100000.0,
        extrapolate_heads_below_minimum=False,
    )
    np.testing.assert_allclose(
        result,
        np.asarray([1.231463064, 0.878913798, 1.323778851, 1.026897386, 0.878913798, 0.730015921, 0.730015921])
        * 4000.0,
        rtol=1e-3,
    )


def test_compressor_chart_generic_mixed_chart_areas(generic_compressor_chart):
    """Testing different chart areas with choking:
    0) internal point
    1) point left of minimum flow
    2) point below minimum speed
    3) point below stone wall
    4) point right of maximum speed line (infeasible)
    5) point above maximum speed.
    """
    actual_volume_rates = np.asarray([3000.0, 2400.0, 2500.0, 4000.0, 5500.0, 4500.0])
    heads = 1000.0 * np.asarray([60.0, 80.0, 45.0, 50.0, 50.0, 115.0])

    # With choking
    compressor_chart_result = generic_compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
        actual_volume_rates=actual_volume_rates,
        heads=heads,
        extrapolate_heads_below_minimum=True,
    )

    indices_asv_not_used = [0, 2, 3, 4, 5]
    np.testing.assert_allclose(
        np.asarray(compressor_chart_result.asv_corrected_rates)[indices_asv_not_used],
        actual_volume_rates[indices_asv_not_used],
    )
    assert compressor_chart_result.asv_corrected_rates[1] > actual_volume_rates[1]
    assert (~np.asarray(compressor_chart_result.rate_has_recirc)[indices_asv_not_used]).all()
    assert compressor_chart_result.rate_has_recirc[1]

    indices_choke_not_used = [0, 1, 5]
    indices_choked = [2, 3, 4]
    np.testing.assert_allclose(
        np.asarray(compressor_chart_result.choke_corrected_heads)[indices_choke_not_used],
        heads[indices_choke_not_used],
    )
    assert np.all(np.asarray(compressor_chart_result.choke_corrected_heads)[indices_choked] > heads[indices_choked])
    assert np.asarray(compressor_chart_result.pressure_is_choked)[indices_choked].all()
    assert (~np.asarray(compressor_chart_result.pressure_is_choked)[indices_choke_not_used]).all()

    indices_rate_exceeds_maximum = [4, 5]
    assert np.asarray(compressor_chart_result.rate_exceeds_maximum)[indices_rate_exceeds_maximum].all()

    indices_invalid_points = [4, 5]
    assert np.asarray(compressor_chart_result.exceeds_capacity)[indices_invalid_points].all()
    assert (
        ~np.asarray(compressor_chart_result.exceeds_capacity)[
            [i for i in range(len(compressor_chart_result.exceeds_capacity)) if i not in indices_invalid_points]
        ]
    ).all()


def test_compressor_chart_generic_mixed_chart_areas_without_choking(generic_compressor_chart):
    """Testing different chart areas without choking:
    0) internal point
    1) point left of minimum flow
    2) point below minimum speed
    3) point below stone wall
    4) point right of maximum speed line (infeasible)
    5) point above maximum speed.
    """
    actual_volume_rates = np.asarray([3000.0, 2400.0, 2500.0, 4000.0, 5500.0, 4500.0])
    heads = 1000.0 * np.asarray([60.0, 80.0, 45.0, 50.0, 50.0, 115.0])

    # Without choking
    compressor_chart_result_without_choking = generic_compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
        actual_volume_rates=actual_volume_rates,
        heads=heads,
        extrapolate_heads_below_minimum=False,
    )

    indices_asv_not_used = [0, 3, 4, 5]
    indices_asv_used = [1, 2]
    np.testing.assert_allclose(
        np.asarray(compressor_chart_result_without_choking.asv_corrected_rates)[indices_asv_not_used],
        actual_volume_rates[indices_asv_not_used],
    )
    assert np.all(
        np.asarray(compressor_chart_result_without_choking.asv_corrected_rates)[indices_asv_used]
        > actual_volume_rates[indices_asv_used]
    )
    assert (~np.asarray(compressor_chart_result_without_choking.rate_has_recirc)[indices_asv_not_used]).all()
    assert np.asarray(compressor_chart_result_without_choking.rate_has_recirc)[indices_asv_used].all()

    np.testing.assert_allclose(
        compressor_chart_result_without_choking.choke_corrected_heads,
        heads,
    )
    assert (~np.asarray(compressor_chart_result_without_choking.pressure_is_choked)).all()

    indices_rate_exceeds_maximum = [4, 5]
    assert np.asarray(compressor_chart_result_without_choking.rate_exceeds_maximum)[indices_rate_exceeds_maximum].all()

    indices_invalid_points = [3, 4, 5]
    assert np.asarray(compressor_chart_result_without_choking.exceeds_capacity)[indices_invalid_points].all()
    assert (
        ~np.asarray(compressor_chart_result_without_choking.exceeds_capacity)[
            [
                i
                for i in range(len(compressor_chart_result_without_choking.exceeds_capacity))
                if i not in indices_invalid_points
            ]
        ]
    ).all()


def test_compressor_chart_from_head_and_rate_data():
    """Test that the design head and rate stays the same (snapshot)."""
    compressor_chart = CompressorChartCreator.from_rate_and_head_values(
        actual_volume_rates_m3_per_hour=[10, 20, 30],
        heads_joule_per_kg=[10, 20, 30],
        polytropic_efficiency=1,
    )

    # Test values are pinned from earlier implementation. Assuming all correct. We should add additional tests.
    assert compressor_chart.data_transfer_object.design_head == pytest.approx(27.534086941946008)
    assert compressor_chart.data_transfer_object.design_rate == pytest.approx(26.780779421483064)


def test_compressor_chart_from_head_and_rate_data_2():
    """Check that we keep the input design head and rate."""
    compressor_chart = CompressorChartCreator.from_rate_and_head_design_point(
        design_actual_rate_m3_per_hour=4000.0,
        design_head_joule_per_kg=100000.0,
        polytropic_efficiency=0.8,
    )

    assert compressor_chart.data_transfer_object.design_head == 100000
    assert compressor_chart.data_transfer_object.design_rate == 4000
