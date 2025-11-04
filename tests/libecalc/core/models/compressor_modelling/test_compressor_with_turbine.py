import numpy as np
import pytest

from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel


@pytest.fixture()
def compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine(
    turbine_factory,
    variable_speed_compressor_train_two_compressors_one_stream,
) -> CompressorWithTurbineModel:
    return CompressorWithTurbineModel(
        turbine_model=turbine_factory(),
        compressor_energy_function=variable_speed_compressor_train_two_compressors_one_stream,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )


def test_variable_speed_multiple_streams_and_pressures_with_turbine(
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine,
):
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine.set_evaluation_input(
        rate=np.asarray([[3000000]]),
        suction_pressure=np.asarray([30]),
        intermediate_pressure=np.array([65]),
        discharge_pressure=np.asarray([100]),
    )
    result_with_turbine = compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine.evaluate()

    expected_load = (
        compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine._energy_usage_adjustment_factor
        * sum([stage.power[0] for stage in result_with_turbine.stage_results])
        + compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine._energy_usage_adjustment_constant
    )
    assert result_with_turbine.turbine_result.get_energy_result().power.values[0] == expected_load


def test_turbine_max_rate(turbine_factory, single_speed_compressor_train_unisim_methane):
    """
    Test that compressor with turbine doesn't affect max_rate when max_load is above power consumption of train.

    Also tests that get_max_standard_rate for compressor with turbine runs without errors.
    """
    compressor_with_turbine_model = CompressorWithTurbineModel(
        turbine_model=turbine_factory(
            loads=[1, 10], efficiency_fractions=[0.5, 0.5]
        ),  # Max power 10, make sure above power from compressor model
        compressor_energy_function=single_speed_compressor_train_unisim_methane,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )
    suction_pressure = np.asarray([40, 40, 40, 35, 60])
    discharge_pressure = np.asarray([200, 200, 200, 200, 200])
    max_rate = compressor_with_turbine_model.get_max_standard_rate(
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
    )

    assert (
        max_rate.tolist()
        == single_speed_compressor_train_unisim_methane.get_max_standard_rate(
            suction_pressures=suction_pressure, discharge_pressures=discharge_pressure
        ).tolist()
    )
