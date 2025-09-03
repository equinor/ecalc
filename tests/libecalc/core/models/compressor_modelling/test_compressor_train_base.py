from unittest.mock import patch, Mock

import numpy as np
import pytest

from libecalc.domain.process.compressor import dto
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain


@pytest.fixture
@patch.multiple(CompressorTrainModel, __abstractmethods__=set())
def compressor_train(variable_speed_compressor_train_dto: dto.VariableSpeedCompressorTrain) -> CompressorTrainModel:
    fluid_factory_mock = Mock()
    stages = [
        map_compressor_train_stage_to_domain(stage_dto)
        for stage_dto in variable_speed_compressor_train_two_stages_dto.stages
    ]
    return CompressorTrainModel(
        fluid_factory=fluid_factory_mock,
        energy_usage_adjustment_constant=variable_speed_compressor_train_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=variable_speed_compressor_train_dto.energy_usage_adjustment_factor,
        stages=stages,
        typ=variable_speed_compressor_train_dto.typ,
        maximum_power=variable_speed_compressor_train_dto.maximum_power,
        pressure_control=variable_speed_compressor_train_dto.pressure_control,
        calculate_max_rate=variable_speed_compressor_train_dto.calculate_max_rate,
    )


@pytest.fixture
@patch.multiple(CompressorTrainModel, __abstractmethods__=set())
def compressor_train_two_stages(
    variable_speed_compressor_train_two_stages_dto: dto.VariableSpeedCompressorTrain,
) -> CompressorTrainModel:
    stages = [
        map_compressor_train_stage_to_domain(stage_dto)
        for stage_dto in variable_speed_compressor_train_two_stages_dto.stages
    ]
    fluid_factory_mock = Mock()
    return CompressorTrainModel(
        fluid_factory=fluid_factory_mock,
        energy_usage_adjustment_constant=variable_speed_compressor_train_two_stages_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=variable_speed_compressor_train_two_stages_dto.energy_usage_adjustment_factor,
        stages=stages,
        typ=variable_speed_compressor_train_two_stages_dto.typ,
        maximum_power=variable_speed_compressor_train_two_stages_dto.maximum_power,
        pressure_control=variable_speed_compressor_train_two_stages_dto.pressure_control,
        calculate_max_rate=variable_speed_compressor_train_two_stages_dto.calculate_max_rate,
    )


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
