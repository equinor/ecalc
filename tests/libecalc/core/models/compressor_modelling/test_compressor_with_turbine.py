import numpy as np
import pytest

from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition, EoSModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


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
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine, fluid_factory_medium
):
    compressor_train_variable_speed_multiple_streams_and_pressures_with_turbine.set_evaluation_input(
        fluid_factory=[fluid_factory_medium],
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
    fluid_factory = NeqSimFluidFactory(FluidModel(composition=FluidComposition(methane=1.0), eos_model=EoSModel.SRK))
    compressor_with_turbine_model = CompressorWithTurbineModel(
        turbine_model=turbine_factory(
            loads=[1, 12], efficiency_fractions=[0.5, 0.5]
        ),  # Max power 10, make sure above power from compressor model
        compressor_energy_function=single_speed_compressor_train_unisim_methane,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )
    rate = np.asarray([1, 1, 1], dtype=float)
    suction_pressure = np.asarray([40, 35, 60], dtype=float)
    discharge_pressure = np.asarray([90, 80, 90], dtype=float)
    compressor_with_turbine_model.set_evaluation_input(
        fluid_factory=fluid_factory,
        rate=rate,
        suction_pressure=suction_pressure,
        discharge_pressure=discharge_pressure,
    )
    max_rate = compressor_with_turbine_model.get_max_standard_rate()

    assert max_rate.tolist() == single_speed_compressor_train_unisim_methane.get_max_standard_rate().tolist()
