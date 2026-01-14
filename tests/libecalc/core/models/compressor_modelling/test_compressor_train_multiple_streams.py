import numpy as np
import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl, InterstagePressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft_multiple_streams_and_pressures import (
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel

DEFAULT_RATE = np.asarray([1])
DEFAULT_SUCTION_PRESSURE = np.asarray([30])
DEFAULT_DISCHARGE_PRESSURE = np.asarray([100])


def calculate_relative_difference(value1, value2):
    return (value1 - value2) / value1 * 100


@pytest.fixture
def variable_speed_compressor_train_multiple_streams_and_pressures(
    fluid_model_medium, compressor_stages, process_simulator_variable_compressor_chart, fluid_service
):
    def create_compressor_train(
        shaft: VariableSpeedShaft | None = None,
        fluid_model: FluidModel = None,
        fluid_streams: list[FluidStreamObjectForMultipleStreams] = None,
        energy_adjustment_constant: float = 0.0,
        energy_adjustment_factor: float = 1.0,
        stages: list[CompressorTrainStage] = None,
        pressure_control: FixedSpeedPressureControl = FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        maximum_power: float = None,
        nr_stages: int = 1,
    ) -> CompressorTrainCommonShaftMultipleStreamsAndPressures:
        if fluid_model is None:
            fluid_model = fluid_model_medium
        if fluid_streams is None:
            fluid_streams = [
                FluidStreamObjectForMultipleStreams(
                    fluid_model=fluid_model, is_inlet_stream=True, connected_to_stage_no=0
                )
            ]
        additional_fluid_streams = fluid_streams[1:] if len(fluid_streams) > 1 else []
        if shaft is None:
            shaft = VariableSpeedShaft()
        if stages is None:
            stages = []
            for i in range(nr_stages):
                stages.append(
                    compressor_stages(
                        shaft=shaft,
                        chart_data=process_simulator_variable_compressor_chart,
                        nr_stages=1,
                        additional_fluid_streams=[
                            fluid_streams
                            for fluid_streams in additional_fluid_streams
                            if fluid_streams.connected_to_stage_no == i
                        ],
                    )[0]
                )

        has_interstage_pressure = any(stage.interstage_pressure_control is not None for stage in stages)
        stage_number_interstage_pressure = (
            [i for i, stage in enumerate(stages) if stage.interstage_pressure_control is not None][0]
            if has_interstage_pressure
            else None
        )

        return CompressorTrainCommonShaftMultipleStreamsAndPressures(
            shaft=shaft,
            streams=fluid_streams,
            fluid_service=fluid_service,
            energy_usage_adjustment_constant=energy_adjustment_constant,
            energy_usage_adjustment_factor=energy_adjustment_factor,
            stages=stages,
            pressure_control=pressure_control,
            maximum_power=maximum_power,
            stage_number_interstage_pressure=stage_number_interstage_pressure,
        )

    return create_compressor_train


@pytest.fixture
def two_streams(fluid_model_medium) -> list[FluidStreamObjectForMultipleStreams]:
    return [
        FluidStreamObjectForMultipleStreams(
            fluid_model=fluid_model_medium,
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
        FluidStreamObjectForMultipleStreams(
            is_inlet_stream=False,
            fluid_model=None,
            connected_to_stage_no=1,
        ),
    ]


def set_evaluation_input(fluid_model, compressor_train: CompressorTrainCommonShaft) -> CompressorTrainCommonShaft:
    compressor_train.set_evaluation_input(
        fluid_model=fluid_model,
        rate=DEFAULT_RATE,
        suction_pressure=DEFAULT_SUCTION_PRESSURE,
        discharge_pressure=DEFAULT_DISCHARGE_PRESSURE,
    )
    return compressor_train


@pytest.mark.slow
def test_get_maximum_standard_rate_max_speed_curve(
    variable_speed_compressor_train,
    variable_speed_compressor_train_multiple_streams_and_pressures,
    fluid_model_medium,
):
    compressor_train = variable_speed_compressor_train(nr_stages=2)
    compressor_train_multiple_streams = variable_speed_compressor_train_multiple_streams_and_pressures(nr_stages=2)
    compressor_train = set_evaluation_input(fluid_model_medium, compressor_train)
    compressor_train_multiple_streams = set_evaluation_input([fluid_model_medium], compressor_train_multiple_streams)

    """Values are pinned against self. Need QA."""
    # Low pressure - outside right end of max speed curve
    outside_curve = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([100]),
    )
    outside_curve_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([100]),
    )

    # Right edge of max speed curve (critical boundary)
    right_end_of_max_speed_curve = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([295.1]),
    )
    right_end_of_max_speed_curve_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([295.1]),
    )

    # Middle pressure - middle of max speed curve
    middle_of_max_speed_curve = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([350]),
    )
    middle_of_max_speed_curve_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([350]),
    )

    # High pressure - left end of max speed curve
    left_end_of_max_speed_curve = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([400]),
    )
    left_end_of_max_speed_curve_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([400]),
    )

    # Assert that variable speed and variable speed with one stream give same results
    np.testing.assert_allclose(outside_curve, outside_curve_multiple_streams, rtol=0.01)
    np.testing.assert_allclose(right_end_of_max_speed_curve, right_end_of_max_speed_curve_multiple_streams, rtol=0.01)
    np.testing.assert_allclose(middle_of_max_speed_curve, middle_of_max_speed_curve_multiple_streams, rtol=0.01)
    np.testing.assert_allclose(left_end_of_max_speed_curve, left_end_of_max_speed_curve_multiple_streams, rtol=0.01)

    # Verify pressure control: pressures at/beyond max rate point give same result
    np.testing.assert_allclose(right_end_of_max_speed_curve, outside_curve, rtol=0.01)

    # Verify expected values at key points
    np.testing.assert_allclose(middle_of_max_speed_curve, 4396383, rtol=0.01)
    np.testing.assert_allclose(left_end_of_max_speed_curve, 3154507, rtol=0.01)


@pytest.mark.slow
def test_get_maximum_standard_rate_at_stone_wall(
    variable_speed_compressor_train,
    variable_speed_compressor_train_multiple_streams_and_pressures,
    fluid_model_medium,
):
    compressor_train = variable_speed_compressor_train(
        pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE, nr_stages=2
    )
    compressor_train_multiple_streams = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2, pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE
    )
    compressor_train = set_evaluation_input(fluid_model_medium, compressor_train)
    compressor_train_multiple_streams = set_evaluation_input([fluid_model_medium], compressor_train_multiple_streams)

    """Values are pinned against self. Need QA."""
    below_stone_wall = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([50.0]),
    )
    below_stone_wall_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([50.0]),
    )

    maximum_rate_stone_wall_100 = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([100.0]),
    )

    maximum_rate_stone_wall_100_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([100.0]),
    )

    maximum_rate_stone_wall_200 = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([200.0]),
    )

    maximum_rate_stone_wall_200_multiple_streams = compressor_train_multiple_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([200.0]),
    )

    np.testing.assert_allclose(below_stone_wall, 0.0)
    np.testing.assert_allclose(maximum_rate_stone_wall_100, 3457025, rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_200, 4467915, rtol=0.01)
    np.testing.assert_allclose(below_stone_wall, below_stone_wall_multiple_streams, rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_100, maximum_rate_stone_wall_100_multiple_streams, rtol=0.01)
    np.testing.assert_allclose(maximum_rate_stone_wall_200, maximum_rate_stone_wall_200_multiple_streams, rtol=0.01)


def test_variable_speed_multiple_streams_and_pressures_maximum_power(
    variable_speed_compressor_train_multiple_streams_and_pressures,
    fluid_model_medium,
):
    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(maximum_power=7)
    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[3000000, 3500000]]),
        suction_pressure=np.asarray([30, 30]),
        discharge_pressure=np.asarray([100, 100]),
    )
    result_variable_speed_compressor_train_one_compressor_one_stream_maximum_power = compressor_train.evaluate()

    energy_result = result_variable_speed_compressor_train_one_compressor_one_stream_maximum_power.get_energy_result()
    assert energy_result.is_valid == [True, False]
    assert result_variable_speed_compressor_train_one_compressor_one_stream_maximum_power.failure_status == [
        CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER,
    ]


@pytest.mark.slow
def test_variable_speed_vs_variable_speed_multiple_streams_and_pressures(
    variable_speed_compressor_train,
    variable_speed_compressor_train_multiple_streams_and_pressures,
    fluid_model_medium,
):
    compressor_train_one_compressor = variable_speed_compressor_train(nr_stages=1)
    compressor_train_two_compressors = variable_speed_compressor_train(nr_stages=2)
    compressor_train_multiple_streams_one_compressor = variable_speed_compressor_train_multiple_streams_and_pressures()
    compressor_train_multiple_streams_two_compressors = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2
    )

    compressor_train_one_compressor.set_evaluation_input(
        fluid_model=fluid_model_medium,
        rate=np.asarray([3000000]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result_variable_speed_compressor_train_one_compressor = compressor_train_one_compressor.evaluate()
    compressor_train_two_compressors.set_evaluation_input(
        fluid_model=fluid_model_medium,
        rate=np.asarray([2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000]),
        suction_pressure=np.asarray([30, 30, 30, 30, 30, 30, 30, 30]),
        discharge_pressure=np.asarray([100.0, 110, 120, 130, 140, 150, 160, 170]),
    )
    result_variable_speed_compressor_train_two_compressors = compressor_train_two_compressors.evaluate()

    compressor_train_multiple_streams_one_compressor.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result_variable_speed_compressor_train_one_compressor_one_stream = (
        compressor_train_multiple_streams_one_compressor.evaluate()
    )
    compressor_train_multiple_streams_two_compressors.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000]]),
        suction_pressure=np.asarray([30, 30, 30, 30, 30, 30, 30, 30], dtype=float),
        discharge_pressure=np.asarray([100.0, 110, 120, 130, 140, 150, 160, 170], dtype=float),
    )
    result_variable_speed_compressor_train_two_compressors_one_stream = (
        compressor_train_multiple_streams_two_compressors.evaluate()
    )
    energy_result_variable_speed_compressor_train_one_compressor_one_stream = (
        result_variable_speed_compressor_train_one_compressor_one_stream.get_energy_result()
    )
    energy_result_variable_speed_compressor_train_one_compressor = (
        result_variable_speed_compressor_train_one_compressor.get_energy_result()
    )
    assert (
        energy_result_variable_speed_compressor_train_one_compressor.energy_usage.values
        == energy_result_variable_speed_compressor_train_one_compressor_one_stream.energy_usage.values
    )
    assert (
        result_variable_speed_compressor_train_one_compressor.stage_results[0].speed
        == result_variable_speed_compressor_train_one_compressor_one_stream.stage_results[0].speed
    )
    energy_result_variable_speed_compressor_train_two_compressors = (
        result_variable_speed_compressor_train_two_compressors.get_energy_result()
    )
    energy_result_variable_speed_compressor_train_two_compressors_one_stream = (
        result_variable_speed_compressor_train_two_compressors_one_stream.get_energy_result()
    )
    assert (
        energy_result_variable_speed_compressor_train_two_compressors.energy_usage.values[1]
        == energy_result_variable_speed_compressor_train_two_compressors_one_stream.energy_usage.values[1]
    )
    assert (
        result_variable_speed_compressor_train_two_compressors.stage_results[1].speed
        == result_variable_speed_compressor_train_two_compressors_one_stream.stage_results[1].speed
    )


def test_points_within_capacity_two_compressors_two_streams(
    variable_speed_compressor_train_multiple_streams_and_pressures,
    two_streams,
    fluid_model_medium,
):
    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2,
        fluid_streams=two_streams,
    )
    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[6000], [2000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([110.0]),
    )
    energy_result = compressor_train.evaluate().get_energy_result()
    assert all(energy_result.is_valid)


@pytest.mark.slow
def test_get_maximum_standard_rate_too_high_pressure_ratio(
    variable_speed_compressor_train,
    variable_speed_compressor_train_multiple_streams_and_pressures,
    two_streams,
    fluid_model_medium,
):
    fluid_streams = two_streams
    fluid_streams[1].fluid_model = fluid_model_medium
    fluid_streams[1].is_inlet_stream = True

    compressor_train = variable_speed_compressor_train(nr_stages=2)
    compressor_train_multiple_streams_one_stream = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2
    )
    compressor_train_multiple_streams_two_streams = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2,
        fluid_streams=fluid_streams,
    )
    compressor_train = set_evaluation_input(fluid_model_medium, compressor_train)
    compressor_train_multiple_streams_one_stream = set_evaluation_input(
        [fluid_model_medium], compressor_train_multiple_streams_one_stream
    )
    compressor_train_multiple_streams_two_streams = set_evaluation_input(
        [fluid_model_medium, fluid_model_medium], compressor_train_multiple_streams_two_streams
    )

    """Values are pinned against self. Need QA."""
    # Check point where head requirement is too high. ASV should make no difference here.
    maximum_rate_max_not_existing = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([1000.0]),
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)
    # Same for multiple streams and pressures train with one stream
    maximum_rate_max_not_existing = compressor_train_multiple_streams_one_stream.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([1000.0]),
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)

    # Same for multiple streams and pressures train with two streams
    maximum_rate_max_not_existing = compressor_train_multiple_streams_two_streams.get_max_standard_rate(
        suction_pressures=np.asarray([30.0]),
        discharge_pressures=np.asarray([1000.0]),
    )
    np.testing.assert_allclose(maximum_rate_max_not_existing, 0)


def test_zero_rate_zero_pressure_multiple_streams(
    variable_speed_compressor_train_multiple_streams_and_pressures, fluid_model_medium, two_streams
):
    """We want to get a result object when rate is zero regardless of invalid/zero pressures. To ensure
    this we set pressure -> 1 when both rate and pressure is zero. This may happen when pressure is a function
    of rate.
    """
    fluid_streams = two_streams
    fluid_streams[1].fluid_model = fluid_model_medium
    fluid_streams[1].is_inlet_stream = True

    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2, fluid_streams=fluid_streams
    )
    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium, fluid_model_medium],
        rate=np.array([[0, 1, 0, 1], [0, 1, 1, 0]]),
        suction_pressure=np.array([0, 1, 1, 1]),
        discharge_pressure=np.array([0, 5, 5, 5]),
    )
    result = compressor_train.evaluate()

    # Ensuring that first stage returns zero energy usage and no failure (zero rate should always be valid).
    energy_result = result.get_energy_result()
    assert energy_result.is_valid == [True, True, True, True]
    assert energy_result.power.values[0] == 0
    np.testing.assert_allclose(
        energy_result.energy_usage.values, np.array([0.0, 0.38390646, 0.38390646, 0.38390646]), rtol=0.0001
    )

    assert result.failure_status == [
        CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
    ]
    assert np.isnan(result.mass_rate_kg_per_hr[0])


def test_different_volumes_of_ingoing_and_outgoing_streams(
    variable_speed_compressor_train_multiple_streams_and_pressures,
    two_streams,
    fluid_model_medium,
):
    """Make sure that we get NOT_CALCULATED if the requested volume leaving the compressor train exceeds the
    volume entering the compressor train.
    """
    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2, fluid_streams=two_streams
    )
    compressor_train.stages[1].interstage_pressure_control = InterstagePressureControl(
        downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
    )

    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium, fluid_model_medium],
        rate=np.array([[0, 0, 100000], [0, 107000, 107000]]),
        suction_pressure=np.array([1, 1, 1]),
        intermediate_pressure=np.array([2, 2, 2]),
        discharge_pressure=np.array([3, 3, 3]),
    )
    result = compressor_train.evaluate()

    assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[1] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[2] == ChartAreaFlag.NOT_CALCULATED

    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium, fluid_model_medium],
        rate=np.array([[0, 0, 100000], [0, 107000, 107000]]),
        suction_pressure=np.array([1, 1, 1]),
        intermediate_pressure=np.array([2, 2, 2]),
        discharge_pressure=np.array([3, 3, 3]),
    )
    result = compressor_train.evaluate()

    assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[1] == ChartAreaFlag.NOT_CALCULATED
    assert result.stage_results[0].chart_area_flags[2] == ChartAreaFlag.NOT_CALCULATED


def test_evaluate_variable_speed_compressor_train_multiple_streams_and_pressures_with_interstage_pressure(
    variable_speed_compressor_train_multiple_streams_and_pressures,
    compressor_stages,
    process_simulator_variable_compressor_chart,
    two_streams,
    fluid_model_medium,
):
    shaft = VariableSpeedShaft()
    stage1 = compressor_stages(shaft=shaft, nr_stages=1, chart_data=process_simulator_variable_compressor_chart)[0]
    stage2 = compressor_stages(
        shaft=shaft,
        additional_fluid_streams=two_streams[1:],  # not the first one
        nr_stages=1,
        chart_data=process_simulator_variable_compressor_chart,
        interstage_pressure_control=InterstagePressureControl(
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
        ),
    )[0]
    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(
        shaft=shaft,
        stages=[stage1, stage2],
        fluid_streams=two_streams,
    )

    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_medium, fluid_model_medium],
        rate=np.array([[1000000, 1200000, 1300000], [0, 107000, 107000]]),
        suction_pressure=np.array([10, 10, 10]),
        intermediate_pressure=np.array([30, 30, 30]),
        discharge_pressure=np.array([90, 90, 90]),
    )
    result = compressor_train.evaluate()

    result_first_stage = result.stage_results[0]
    result_last_stage = result.stage_results[1]
    assert result_first_stage.speed == pytest.approx([10825.72, 11100.26, 11313.19], abs=0.01)
    assert result_first_stage.outlet_stream_condition.pressure == pytest.approx([30.0, 30.0, 30.0], abs=0.01)
    assert result_last_stage.asv_recirculation_loss_mw == pytest.approx([4.22, 4.39, 4.46], abs=0.01)
    assert result_first_stage.speed == result_last_stage.speed


@pytest.mark.parametrize("energy_usage_adjustment_constant", [1, 2, 3, 5, 10])
def test_adjust_energy_usage(
    energy_usage_adjustment_constant,
    variable_speed_compressor_train_multiple_streams_and_pressures,
    compressor_stages,
    fluid_model_medium,
    two_streams,
    process_simulator_variable_compressor_chart,
):
    shaft = VariableSpeedShaft()
    compressor_train_one_compressor_one_stream_downstream_choke = (
        variable_speed_compressor_train_multiple_streams_and_pressures(shaft=shaft)
    )
    compressor_train_one_compressor_one_stream_downstream_choke.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result_comparison = compressor_train_one_compressor_one_stream_downstream_choke.evaluate()

    stage1 = compressor_stages(shaft=shaft, nr_stages=1, chart_data=process_simulator_variable_compressor_chart)[0]
    stage2 = compressor_stages(
        shaft=shaft,
        nr_stages=1,
        chart_data=process_simulator_variable_compressor_chart,
        interstage_pressure_control=InterstagePressureControl(
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
        ),
    )[0]
    compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream = (
        variable_speed_compressor_train_multiple_streams_and_pressures(
            shaft=shaft,
            stages=[stage1, stage2],
            fluid_streams=two_streams,
        )
    )
    compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.set_evaluation_input(
        fluid_model=[fluid_model_medium, fluid_model_medium],
        rate=np.array([[1000000], [0]]),
        suction_pressure=np.array([10]),
        intermediate_pressure=np.array([30]),
        discharge_pressure=np.array([90]),
    )

    result_comparison_intermediate = compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate()

    compressor_train_one_compressor_one_stream_downstream_choke.energy_usage_adjustment_constant = (
        energy_usage_adjustment_constant  # MW
    )
    compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.energy_usage_adjustment_constant = (
        energy_usage_adjustment_constant
    )

    compressor_train_one_compressor_one_stream_downstream_choke.set_evaluation_input(
        fluid_model=[fluid_model_medium],
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )
    result = compressor_train_one_compressor_one_stream_downstream_choke.evaluate()
    result_intermediate = compressor_train_two_compressors_one_ingoing_and_one_outgoing_stream.evaluate()

    energy_result_comparison = result_comparison.get_energy_result()
    energy_result = result.get_energy_result()

    np.testing.assert_allclose(
        np.asarray(energy_result_comparison.energy_usage.values) + energy_usage_adjustment_constant,
        energy_result.energy_usage.values,
    )
    energy_result_comparison_intermediate = result_comparison_intermediate.get_energy_result()
    energy_result_intermediate = result_intermediate.get_energy_result()
    np.testing.assert_allclose(
        np.asarray(energy_result_comparison_intermediate.energy_usage.values) + energy_usage_adjustment_constant,
        energy_result_intermediate.energy_usage.values,
    )


def test_recirculate_mixing_streams_with_zero_mass_rate(
    fluid_model_rich,
    fluid_model_dry,
    variable_speed_compressor_train_multiple_streams_and_pressures,
):
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid_model=fluid_model_rich,
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
        FluidStreamObjectForMultipleStreams(
            is_inlet_stream=False,
            connected_to_stage_no=1,
        ),
        FluidStreamObjectForMultipleStreams(
            fluid_model=fluid_model_dry,
            is_inlet_stream=True,
            connected_to_stage_no=1,
        ),
    ]
    compressor_train = variable_speed_compressor_train_multiple_streams_and_pressures(
        nr_stages=2,
        fluid_streams=fluid_streams,
    )
    compressor_train.set_evaluation_input(
        fluid_model=[fluid_model_rich, fluid_model_rich, fluid_model_dry],
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
    result = compressor_train.evaluate()
    energy_result = result.get_energy_result()
    np.testing.assert_almost_equal(energy_result.power.values[0], energy_result.power.values[1], decimal=4)
    np.testing.assert_almost_equal(
        energy_result.power.values[0], energy_result.power.values[3], decimal=4
    )  # recirculating same fluid as in first time step
    np.testing.assert_almost_equal(
        energy_result.power.values[0], energy_result.power.values[5], decimal=4
    )  # recirculating same fluid as in first time step
    assert (
        energy_result.power.values[0] < energy_result.power.values[2] < energy_result.power.values[4]
    )  # more and more of the heavy fluid

    assert result.recirculation_loss[0] < result.recirculation_loss[1]
    assert result.recirculation_loss[2] < result.recirculation_loss[3]
    assert result.recirculation_loss[4] < result.recirculation_loss[5]
    assert result.stage_results[1].chart_area_flags == [
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE.value,
        ChartAreaFlag.NO_FLOW_RATE.value,
    ]
