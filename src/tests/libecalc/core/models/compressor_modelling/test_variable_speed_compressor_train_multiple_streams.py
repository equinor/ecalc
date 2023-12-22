from unittest.mock import MagicMock

import numpy as np
import pytest
from libecalc import dto
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.dto import InterstagePressureControl
from libecalc.dto.types import ChartAreaFlag, FixedSpeedPressureControl


def calculate_relative_difference(value1, value2):
    return (value1 - value2) / value1 * 100


@pytest.fixture
def variable_speed_compressor_train_one_compressor(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only one compressor, and standard medium fluid, no liquid off take."""
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=variable_speed_compressor_train_dto.copy(
            update={"stages": [variable_speed_compressor_train_stage_dto]}
        )
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only two compressors, and standard medium fluid, no liquid off take."""
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=variable_speed_compressor_train_dto.copy(
            update={"stages": [variable_speed_compressor_train_stage_dto] * 2}
        )
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_downstream_choke(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with two compressors, and standard medium fluid, no liquid off take."""
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=variable_speed_compressor_train_dto.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto] * 2,
                "pressure_control": dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            }
        )
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_individual_asv_pressure(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with two compressors, and standard medium fluid, no liquid off take."""
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=variable_speed_compressor_train_dto.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto] * 2,
                "pressure_control": dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
            }
        )
    )


@pytest.fixture
def mock_variable_speed_compressor_train_multiple_streams_and_pressures(
    variable_speed_compressor_chart_dto,
) -> dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures:
    stream = MagicMock(dto.MultipleStreamsAndPressureStream)
    stage = dto.MultipleStreamsCompressorStage(
        compressor_chart=variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=0,
        control_margin=0,
    )
    return dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures(
        streams=[stream] * 2,
        stages=[stage] * 2,
        calculate_max_rate=False,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        pressure_control=dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
    )


@pytest.fixture
def variable_speed_compressor_train_one_compressor_one_stream(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only one compressor, and standard medium fluid, no liquid off take,
    using multiple streams and pressures class.
    """
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=[
            FluidStreamObjectForMultipleStreams(
                fluid=FluidStream(medium_fluid), is_inlet_stream=True, connected_to_stage_no=0
            )
        ],
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={"stages": [variable_speed_compressor_train_stage_dto]}
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_one_compressor_one_stream_downstream_choke(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only one compressor, and standard medium fluid, no liquid off take,
    using multiple streams and pressures class.
    """
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=[
            FluidStreamObjectForMultipleStreams(
                fluid=FluidStream(medium_fluid), is_inlet_stream=True, connected_to_stage_no=0
            )
        ],
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto],
                "pressure_control": dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            }
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_stream_downstream_choke(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, one stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto] * 2,
                "pressure_control": dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            }
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_stream_individual_asv_pressure(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, one stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto] * 2,
                "pressure_control": dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
            }
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_two_streams(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, on stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=1,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={"stages": [variable_speed_compressor_train_stage_dto] * 2}
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_ingoning_and_outgoing_streams_between_compressors(
    variable_speed_compressor_train_stage_dto,
    dry_fluid,
    rich_fluid,
    mock_variable_speed_compressor_train_multiple_streams_and_pressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, on stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(rich_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
        FluidStreamObjectForMultipleStreams(
            is_inlet_stream=False,
            connected_to_stage_no=1,
        ),
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(dry_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=1,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures.copy(
            update={
                "stages": [variable_speed_compressor_train_stage_dto] * 2,
                "pressure_control": dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            }
        ),
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream(
    variable_speed_compressor_train_stage_dto,
    medium_fluid,
    variable_speed_compressor_chart_dto,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, on stream in per stage, no liquid off take."""
    stream = MagicMock(dto.MultipleStreamsAndPressureStream)
    stage = dto.MultipleStreamsCompressorStage(
        compressor_chart=variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=[0] * 3,
        control_margin=0,
    )
    stage2 = dto.MultipleStreamsCompressorStage(
        compressor_chart=variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=[0] * 3,
        control_margin=0,
        interstage_pressure_control=InterstagePressureControl(
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
        ),
    )
    mock_variable_speed_compressor_train_multiple_streams_and_pressures_with_pressure_control = (
        dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures(
            streams=[stream] * 2,
            stages=[stage, stage2],
            calculate_max_rate=False,
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
            pressure_control=dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
        )
    )

    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
        FluidStreamObjectForMultipleStreams(
            is_inlet_stream=False,
            fluid=None,
            connected_to_stage_no=1,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=mock_variable_speed_compressor_train_multiple_streams_and_pressures_with_pressure_control,
    )


@pytest.mark.slow
def test_get_maximum_standard_rate_max_speed_curve(
    variable_speed_compressor_train_two_compressors_downstream_choke,
    variable_speed_compressor_train_two_compressors_one_stream_downstream_choke,
):
    """Values are pinned against self. Need QA."""
    outside_right_end_of_max_speed_curve_1 = (
        variable_speed_compressor_train_two_compressors_downstream_choke.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([100], dtype=float),
        )
    )

    outside_right_end_of_max_speed_curve_1_multiple_streams = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([100], dtype=float),
            rates_per_stream=np.asarray([[100]], dtype=float),
        )
    )

    outside_right_end_of_max_speed_curve_2 = (
        variable_speed_compressor_train_two_compressors_downstream_choke.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([200], dtype=float),
        )
    )

    outside_right_end_of_max_speed_curve_2_multiple_streams = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([200], dtype=float),
            rates_per_stream=np.asarray([[100]], dtype=float),
        )
    )

    right_end_of_max_speed_curve = (
        variable_speed_compressor_train_two_compressors_downstream_choke.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([295.1], dtype=float),
        )
    )
    middle_of_max_speed_curve = variable_speed_compressor_train_two_compressors_downstream_choke.get_max_standard_rate(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([350], dtype=float),
    )
    left_end_of_max_speed_curve = (
        variable_speed_compressor_train_two_compressors_downstream_choke.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([400], dtype=float),
        )
    )

    # Same for multiple streams (one stream)
    right_end_of_max_speed_curve_multiple_streams = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([295.1], dtype=float),
            rates_per_stream=np.asarray([[100]], dtype=float),
        )
    )
    middle_of_max_speed_curve_multiple_streams = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([350], dtype=float),
            rates_per_stream=np.asarray([[100]], dtype=float),
        )
    )
    left_end_of_max_speed_curve_multiple_streams = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([400], dtype=float),
            rates_per_stream=np.asarray([[100]], dtype=float),
        )
    )

    # Assert that variable speed and variable speed with one stream give same results
    np.testing.assert_allclose(
        outside_right_end_of_max_speed_curve_1, outside_right_end_of_max_speed_curve_1_multiple_streams[0], rtol=0.001
    )
    np.testing.assert_allclose(
        outside_right_end_of_max_speed_curve_2, outside_right_end_of_max_speed_curve_2_multiple_streams[0], rtol=0.001
    )

    np.testing.assert_allclose(
        right_end_of_max_speed_curve, right_end_of_max_speed_curve_multiple_streams[0], rtol=0.001
    )
    np.testing.assert_allclose(middle_of_max_speed_curve, middle_of_max_speed_curve_multiple_streams[0], rtol=0.001)
    np.testing.assert_allclose(left_end_of_max_speed_curve, left_end_of_max_speed_curve_multiple_streams[0], rtol=0.001)

    # When using pressure control we same values for everything at the max rate point and above. So at a lower
    # pressure requirement we expect the values to match
    np.testing.assert_allclose(
        outside_right_end_of_max_speed_curve_1, outside_right_end_of_max_speed_curve_2, rtol=0.001
    )
    np.testing.assert_allclose(right_end_of_max_speed_curve, outside_right_end_of_max_speed_curve_1, rtol=0.001)

    np.testing.assert_allclose(middle_of_max_speed_curve, 4396383, rtol=0.001)

    np.testing.assert_allclose(left_end_of_max_speed_curve, 3164249, rtol=0.001)


@pytest.mark.slow
def test_get_maximum_standard_rate_at_stone_wall(
    variable_speed_compressor_train_two_compressors_individual_asv_pressure,
    variable_speed_compressor_train_two_compressors_one_stream_individual_asv_pressure,
):
    """Values are pinned against self. Need QA."""
    below_stone_wall = variable_speed_compressor_train_two_compressors_individual_asv_pressure.get_max_standard_rate(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([50], dtype=float),
    )
    below_stone_wall_multiple_streams = variable_speed_compressor_train_two_compressors_one_stream_individual_asv_pressure.get_max_standard_rate_per_stream(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([50], dtype=float),
        rates_per_stream=np.asarray([[100]], dtype=float),
    )

    maximum_rate_stone_wall_100 = (
        variable_speed_compressor_train_two_compressors_individual_asv_pressure.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([100], dtype=float),
        )
    )

    maximum_rate_stone_wall_100_multiple_streams = variable_speed_compressor_train_two_compressors_one_stream_individual_asv_pressure.get_max_standard_rate_per_stream(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([100], dtype=float),
        rates_per_stream=np.asarray([[100]], dtype=float),
    )

    maximum_rate_stone_wall_200 = (
        variable_speed_compressor_train_two_compressors_individual_asv_pressure.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([200], dtype=float),
        )
    )

    maximum_rate_stone_wall_200_multiple_streams = variable_speed_compressor_train_two_compressors_one_stream_individual_asv_pressure.get_max_standard_rate_per_stream(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([200], dtype=float),
        rates_per_stream=np.asarray([[100]], dtype=float),
    )

    np.testing.assert_allclose(below_stone_wall, 0.0)
    np.testing.assert_allclose(maximum_rate_stone_wall_100, 3457025, rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_200, 4467915, rtol=0.01)
    np.testing.assert_allclose(below_stone_wall, below_stone_wall_multiple_streams[0], rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_100, maximum_rate_stone_wall_100_multiple_streams[0], rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_200, maximum_rate_stone_wall_200_multiple_streams[0], rtol=0.01)


@pytest.mark.slow
def test_variable_speed_vs_variable_speed_multiple_streams_and_pressures(
    variable_speed_compressor_train_one_compressor,
    variable_speed_compressor_train_two_compressors,
    variable_speed_compressor_train_one_compressor_one_stream_downstream_choke,
    variable_speed_compressor_train_two_compressors_one_stream_downstream_choke,
):
    result_variable_speed_compressor_train_one_compressor = (
        variable_speed_compressor_train_one_compressor.evaluate_rate_ps_pd(
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100]),
        )
    )
    result_variable_speed_compressor_train_two_compressors = (
        variable_speed_compressor_train_two_compressors.evaluate_rate_ps_pd(
            rate=np.asarray([2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000]),
            suction_pressure=np.asarray([30, 30, 30, 30, 30, 30, 30, 30]),
            discharge_pressure=np.asarray([100.0, 110, 120, 130, 140, 150, 160, 170]),
        )
    )
    result_variable_speed_compressor_train_one_compressor_one_stream = (
        variable_speed_compressor_train_one_compressor_one_stream_downstream_choke.evaluate_rate_ps_pd(
            rate=np.asarray([[3000000]]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100]),
        )
    )
    result_variable_speed_compressor_train_two_compressors_one_stream = (
        variable_speed_compressor_train_two_compressors_one_stream_downstream_choke.evaluate_rate_ps_pd(
            rate=np.asarray([[2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000]]),
            suction_pressure=np.asarray([30, 30, 30, 30, 30, 30, 30, 30], dtype=float),
            discharge_pressure=np.asarray([100.0, 110, 120, 130, 140, 150, 160, 170], dtype=float),
        )
    )

    assert (
        result_variable_speed_compressor_train_one_compressor.energy_usage
        == result_variable_speed_compressor_train_one_compressor_one_stream.energy_usage
    )
    assert (
        result_variable_speed_compressor_train_one_compressor.stage_results[0].speed
        == result_variable_speed_compressor_train_one_compressor_one_stream.stage_results[0].speed
    )
    assert (
        result_variable_speed_compressor_train_two_compressors.energy_usage[1]
        == result_variable_speed_compressor_train_two_compressors_one_stream.energy_usage[1]
    )
    assert (
        result_variable_speed_compressor_train_two_compressors.stage_results[1].speed
        == result_variable_speed_compressor_train_two_compressors_one_stream.stage_results[1].speed
    )


def test_points_within_capacity_two_compressors_two_streams(
    variable_speed_compressor_train_two_compressors_two_streams,
):
    result = variable_speed_compressor_train_two_compressors_two_streams.evaluate_rate_ps_pd(
        rate=np.asarray([[6000], [2000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([110.0]),
    )
    assert result.energy_usage


@pytest.mark.slow
def test_get_maximum_standard_rate_too_high_pressure_ratio(
    variable_speed_compressor_train_two_compressors,
    variable_speed_compressor_train_two_compressors_one_stream,
    variable_speed_compressor_train_two_compressors_two_streams,
):
    """Values are pinned against self. Need QA."""
    # Check point where head requirement is too high. ASV should make no difference here.
    maximum_rate_max_not_existing = variable_speed_compressor_train_two_compressors.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([1000]),
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)
    # Same for multiple streams and pressures train with one stream
    maximum_rate_max_not_existing = (
        variable_speed_compressor_train_two_compressors_one_stream.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30]),
            discharge_pressures=np.asarray([1000]),
            rates_per_stream=np.asarray([[100]]),
        )
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)

    # Same for multiple streams and pressures train with two streams
    maximum_rate_max_not_existing = (
        variable_speed_compressor_train_two_compressors_two_streams.get_max_standard_rate_per_stream(
            suction_pressures=np.asarray([30]),
            discharge_pressures=np.asarray([1000]),
            rates_per_stream=np.asarray([[100], [100]]),
        )
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)


def test_zero_rate_zero_pressure_multiple_streams(variable_speed_compressor_train_two_compressors_two_streams):
    """We want to get a result object when rate is zero regardless of invalid/zero pressures. To ensure
    this we set pressure -> 1 when both rate and pressure is zero. This may happen when pressure is a function
    of rate.
    """
    result = variable_speed_compressor_train_two_compressors_two_streams.evaluate_rate_ps_pd(
        rate=np.array([[0, 1, 0, 1], [0, 1, 1, 0]]),
        suction_pressure=np.array([0, 1, 1, 1]),
        discharge_pressure=np.array([0, 5, 5, 5]),
    )

    # Ensuring that first stage returns zero energy usage and no failure (zero rate should always be valid).
    assert result.is_valid == [True, True, True, True]
    assert result.failure_status == [
        None,
        None,
        None,
        None,
    ]
    np.testing.assert_allclose(result.energy_usage, np.array([0.0, 0.38390646, 0.38390646, 0.38390646]), rtol=0.0001)

    assert result.mass_rate_kg_per_hr[0] == 0
    assert result.power[0] == 0


def test_different_volumes_of_ingoing_and_outgoing_streams(
    variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream,
):
    """Make sure that we get NOT_CALCULATED if the requested volume leaving the compressor train exceeds the
    volume entering the compressor train.
    """
    result = variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate_rate_ps_pd(
        rate=np.array([[0, 0, 100000], [0, 107000, 107000]]),
        suction_pressure=np.array([1, 1, 1]),
        discharge_pressure=np.array([3, 3, 3]),
    )

    assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[1] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[2] == ChartAreaFlag.NOT_CALCULATED

    result = (
        variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate_rate_ps_pint_pd(
            rate=np.array([[0, 0, 100000], [0, 107000, 107000]]),
            suction_pressure=np.array([1, 1, 1]),
            intermediate_pressure=np.array([2, 2, 2]),
            discharge_pressure=np.array([3, 3, 3]),
        )
    )

    assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[1] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[2] == ChartAreaFlag.NOT_CALCULATED


def test_evaluate_variable_speed_compressor_train_multiple_streams_and_pressures_with_interstage_pressure(
    variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream,
):
    result = (
        variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate_rate_ps_pint_pd(
            rate=np.array([[1000000, 1200000, 1300000], [0, 107000, 107000]]),
            suction_pressure=np.array([10, 10, 10]),
            intermediate_pressure=np.array([30, 30, 30]),
            discharge_pressure=np.array([90, 90, 90]),
        )
    )

    np.testing.assert_allclose(result.stage_results[0].speed, [10850.87, 11118.95, 11321.47], rtol=0.1)
    np.testing.assert_allclose(
        result.stage_results[0].outlet_stream_condition.pressure, np.array([30.0, 30.0, 30.0]), rtol=0.001
    )
    np.testing.assert_allclose(
        result.stage_results[1].asv_recirculation_loss_mw, np.array([4.25, 4.41, 4.46]), rtol=0.01
    )


@pytest.mark.parametrize("energy_usage_adjustment_constant", [1, 2, 3, 5, 10])
def test_adjust_energy_usage(
    variable_speed_compressor_train_one_compressor_one_stream_downstream_choke,
    variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream,
    energy_usage_adjustment_constant,
):
    result_comparison = variable_speed_compressor_train_one_compressor_one_stream_downstream_choke.evaluate_rate_ps_pd(
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result_comparison_intermediate = (
        variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate_rate_ps_pint_pd(
            rate=np.array([[1000000], [0]]),
            suction_pressure=np.array([10]),
            intermediate_pressure=np.array([30]),
            discharge_pressure=np.array([90]),
        )
    )

    variable_speed_compressor_train_one_compressor_one_stream_downstream_choke.data_transfer_object.energy_usage_adjustment_constant = (
        energy_usage_adjustment_constant  # MW
    )
    variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.data_transfer_object.energy_usage_adjustment_constant = (
        energy_usage_adjustment_constant
    )

    result = variable_speed_compressor_train_one_compressor_one_stream_downstream_choke.evaluate_rate_ps_pd(
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result_intermediate = (
        variable_speed_compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate_rate_ps_pint_pd(
            rate=np.array([[1000000], [0]]),
            suction_pressure=np.array([10]),
            intermediate_pressure=np.array([30]),
            discharge_pressure=np.array([90]),
        )
    )

    np.testing.assert_allclose(
        np.asarray(result_comparison.energy_usage) + energy_usage_adjustment_constant, result.energy_usage
    )
    np.testing.assert_allclose(
        np.asarray(result_comparison_intermediate.energy_usage) + energy_usage_adjustment_constant,
        result_intermediate.energy_usage,
    )


def test_recirculate_mixing_streams_with_zero_mass_rate(
    variable_speed_compressor_train_two_compressors_ingoning_and_outgoing_streams_between_compressors,
):
    result = variable_speed_compressor_train_two_compressors_ingoning_and_outgoing_streams_between_compressors.evaluate_rate_ps_pd(
        rate=np.asarray(
            [
                [3000000, 3000000, 3000000, 3000000, 3000000, 3000000],
                [0, 3000000, 2500000, 3000000, 3000000, 3000000],
                [0, 0, 500000, 0, 1000000, 0],
            ]
        ),
        suction_pressure=np.asarray([30, 30, 30, 30, 30, 30]),
        discharge_pressure=np.asarray([150, 150, 150, 150, 150, 150]),
    )
    np.testing.assert_almost_equal(result.power[0], result.power[1], decimal=4)
    np.testing.assert_almost_equal(result.power[2], result.power[3], decimal=4)
    np.testing.assert_almost_equal(result.power[4], result.power[5], decimal=4)
    assert result.recirculation_loss[0] < result.recirculation_loss[1]
    assert result.recirculation_loss[2] < result.recirculation_loss[3]
    assert result.recirculation_loss[4] < result.recirculation_loss[5]
    assert result.power[0] < result.power[2] < result.power[4]  # more and more of the heavy fluid
    assert result.stage_results[1].chart_area_flags == [
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
    ]
