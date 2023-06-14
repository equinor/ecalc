from unittest.mock import patch

import numpy as np
import pytest
from libecalc import dto
from libecalc.core.models.compressor.train.base import CompressorTrainModel
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)


@pytest.fixture
@patch.multiple(CompressorTrainModel, __abstractmethods__=set())
def compressor_train(variable_speed_compressor_train_dto: dto.VariableSpeedCompressorTrain) -> CompressorTrainModel:
    return CompressorTrainModel(variable_speed_compressor_train_dto)


@pytest.fixture
@patch.multiple(CompressorTrainModel, __abstractmethods__=set())
def compressor_train_two_stages(
    variable_speed_compressor_train_two_stages_dto: dto.VariableSpeedCompressorTrain,
) -> CompressorTrainModel:
    return CompressorTrainModel(variable_speed_compressor_train_two_stages_dto)


def test_minimum_speed(compressor_train_two_stages):
    max_min_speed = max(stage.compressor_chart.minimum_speed for stage in compressor_train_two_stages.stages)
    assert compressor_train_two_stages.minimum_speed == max_min_speed


def test_maximum_speed(compressor_train_two_stages):
    min_max_speed = min(stage.compressor_chart.maximum_speed for stage in compressor_train_two_stages.stages)
    assert compressor_train_two_stages.maximum_speed == min_max_speed


def test_calculate_pressure_ratios_per_stage(compressor_train_two_stages):
    pressure_ratios = compressor_train_two_stages.calculate_pressure_ratios_per_stage(
        suction_pressure=np.array([2, 2, 2, 2, 2], dtype=float),
        discharge_pressure=np.array([2, 3, 4, 5, 6], dtype=float),
    )

    np.testing.assert_almost_equal(pressure_ratios, [1.0, 1.22474487, 1.41421356, 1.58113883, 1.73205081])


def test_validate_operational_conditions(compressor_train):
    #  test that valid single stream input is not changed
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [None, None]

    #  test that valid multiple stream input is not changed
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([[1000, 1000], [1000, 1000]]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [None, None]

    # test that suction pressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([-1, 0]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        CompressorTrainCommonShaftFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
        CompressorTrainCommonShaftFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
    ]

    # test that discharge pressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([-1, 0]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 1)
    assert failure_status == [
        CompressorTrainCommonShaftFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
        CompressorTrainCommonShaftFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
    ]

    # test that intermediate prressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([-1, 0]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 1)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        CompressorTrainCommonShaftFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
        CompressorTrainCommonShaftFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
    ]

    # test that rate < 0 is set to 0 for multiple stream compressor train
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([[-1, 1000, 1000], [1000, -1, 1000]]),
        suction_pressure=np.asarray([1, 1, 1]),
        intermediate_pressure=np.asarray([2, 2, 2]),
        discharge_pressure=np.asarray([3, 3, 3]),
    )
    assert np.all(rate[:, 0] == 0)
    assert np.all(rate[:, 1] == 0)
    assert np.all(rate[:, 2] == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        CompressorTrainCommonShaftFailureStatus.INVALID_RATE_INPUT,
        CompressorTrainCommonShaftFailureStatus.INVALID_RATE_INPUT,
        None,
    ]
    # test that rate < 0 is set to 0 for single stream compressor train
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = compressor_train.validate_operational_conditions(
        rate=np.asarray([-1, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert rate[0] == 0
    assert rate[1] == 1000
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [CompressorTrainCommonShaftFailureStatus.INVALID_RATE_INPUT, None]
