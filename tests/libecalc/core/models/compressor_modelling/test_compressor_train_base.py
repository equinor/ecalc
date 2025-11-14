from unittest.mock import Mock, patch

import numpy as np
import pytest

from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel


@pytest.fixture
@patch.multiple(CompressorTrainModel, __abstractmethods__=set())
def compressor_train_two_stages(
    variable_speed_compressor_train,
    compressor_stages,
    variable_speed_compressor_chart_data,
) -> CompressorTrainModel:
    train = variable_speed_compressor_train(
        stages=compressor_stages(
            nr_stages=2, chart_data=variable_speed_compressor_chart_data, remove_liquid_after_cooling=True
        )
    )

    fluid_factory_mock = Mock()
    return CompressorTrainModel(
        fluid_factory=fluid_factory_mock,
        energy_usage_adjustment_constant=train.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=train.energy_usage_adjustment_factor,
        stages=train.stages,
        maximum_power=train.maximum_power,
        pressure_control=train.pressure_control,
        calculate_max_rate=train.calculate_max_rate,
    )


def test_minimum_speed(compressor_train_two_stages):
    max_min_speed = max(stage.compressor.compressor_chart.minimum_speed for stage in compressor_train_two_stages.stages)
    assert compressor_train_two_stages.minimum_speed == max_min_speed


def test_maximum_speed(compressor_train_two_stages):
    min_max_speed = min(stage.compressor.compressor_chart.maximum_speed for stage in compressor_train_two_stages.stages)
    assert compressor_train_two_stages.maximum_speed == min_max_speed


def test_calculate_pressure_ratios_per_stage(compressor_train_two_stages):
    pressure_ratios = compressor_train_two_stages.calculate_pressure_ratios_per_stage(
        suction_pressure=np.array([2, 2, 2, 2, 2], dtype=float),
        discharge_pressure=np.array([2, 3, 4, 5, 6], dtype=float),
    )

    np.testing.assert_almost_equal(pressure_ratios, [1.0, 1.22474487, 1.41421356, 1.58113883, 1.73205081])
