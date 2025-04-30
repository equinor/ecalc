import numpy as np
import pytest

from libecalc.domain.process.compressor import dto
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel


@pytest.fixture()
def compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine_dto(
    variable_speed_compressor_train_two_compressors_one_stream_dto,
    turbine_dto,
) -> dto.CompressorWithTurbine:
    return dto.CompressorWithTurbine(
        compressor_train=variable_speed_compressor_train_two_compressors_one_stream_dto,
        turbine=turbine_dto,
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture()
def compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine(
    turbine_factory,
    variable_speed_compressor_train_two_compressors_one_stream,
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine_dto,
) -> CompressorWithTurbineModel:
    return CompressorWithTurbineModel(
        turbine_model=turbine_factory(),
        compressor_energy_function=variable_speed_compressor_train_two_compressors_one_stream,
        energy_usage_adjustment_constant=compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine_dto.energy_usage_adjustment_factor,
    )


def test_variable_speed_multiple_streams_and_pressures_with_turbine(
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine,
):
    result_with_turbine = compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine.evaluate(
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100]),
    )

    expected_load = (
        compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine._energy_usage_adjustment_factor
        * sum([stage.power[0] for stage in result_with_turbine.stage_results])
        + compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine._energy_usage_adjustment_constant
    )
    assert result_with_turbine.turbine_result.load[0] == expected_load
