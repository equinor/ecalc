from unittest.mock import patch

import numpy as np
import pytest
from libecalc import dto
from libecalc.core.models.compressor.train.base import CompressorTrainModel


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
