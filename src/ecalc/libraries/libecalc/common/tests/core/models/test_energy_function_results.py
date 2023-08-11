import numpy as np
from libecalc.common.units import Unit
from libecalc.core.models.results import (
    CompressorStageResult,
    CompressorTrainResult,
    EnergyFunctionGenericResult,
)


def test_energy_function_result_append_generic_result():
    result = EnergyFunctionGenericResult(
        energy_usage=[1.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1.0],
        power_unit=Unit.MEGA_WATT,
    )

    other_result = EnergyFunctionGenericResult(
        energy_usage=[2.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[2.0],
        power_unit=Unit.MEGA_WATT,
    )

    updated_result = result.extend(other_result)

    np.testing.assert_equal(updated_result.energy_usage, np.array([1.0, 2.0]))
    assert updated_result.energy_usage_unit == Unit.MEGA_WATT
    np.testing.assert_equal(updated_result.power, np.array([1.0, 2.0]))
    assert updated_result.power_unit == Unit.MEGA_WATT


def test_energy_function_result_append_compressor_train_result():
    result = EnergyFunctionGenericResult(
        energy_usage=[1.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1.0],
        power_unit=Unit.MEGA_WATT,
    )

    other_result = EnergyFunctionGenericResult(
        energy_usage=[2.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[2.0],
        power_unit=Unit.MEGA_WATT,
    )

    updated_result = result.extend(other_result)

    np.testing.assert_equal(updated_result.energy_usage, np.array([1.0, 2.0]))
    assert updated_result.energy_usage_unit == Unit.MEGA_WATT
    np.testing.assert_equal(updated_result.power, np.array([1.0, 2.0]))
    assert updated_result.power_unit == Unit.MEGA_WATT


def test_extend_mismatching_compressor_stage_results():
    """First result has 0 stage results. This simulates a tabulated Compressor or similar.
    The second result has 2 stages. This simulates a fully specified model.
    The third result has 1 stage. This simulates that one stage is decommissioned.
    :return:
    """
    result_1 = CompressorTrainResult(
        energy_usage=[1.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )
    result_2 = CompressorTrainResult(
        energy_usage=[2.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult.create_empty(number_of_timesteps=3),
            CompressorStageResult.create_empty(number_of_timesteps=3),
        ],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )
    result_3 = CompressorTrainResult(
        energy_usage=[3.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[CompressorStageResult.create_empty(number_of_timesteps=3)],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )

    result_4 = CompressorTrainResult(
        energy_usage=[],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[],
        power_unit=Unit.MEGA_WATT,
        stage_results=[],
        rate_sm3_day=[],
        failure_status=[],
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )

    result = result_1.copy()
    for temporal_result in [result_2, result_3, result_4]:
        result.extend(temporal_result)

    assert result.energy_usage == [1, 1, 1, 2, 2, 2, 3, 3, 3]
    assert len(result.stage_results) == 2
    for stage_result in result.stage_results:
        assert len(stage_result.energy_usage) == 9


def test_extend_compressor_train_result_from_multiple_streams() -> None:
    """For a compressor train with multiple inlet/outlet streams rate_sm3_day will be a list of lists
    Make sure that extend preserves this by extending each list within a list.
    """
    result_1 = CompressorTrainResult(
        energy_usage=[1.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[],
        rate_sm3_day=[[1] * 3] * 3,
        failure_status=[None] * 3,
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )
    result_2 = CompressorTrainResult(
        energy_usage=[2.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult.create_empty(number_of_timesteps=3),
            CompressorStageResult.create_empty(number_of_timesteps=3),
        ],
        rate_sm3_day=[[2] * 3] * 3,
        failure_status=[None] * 3,
        requested_inlet_pressure=[np.nan] * 3,
        requested_outlet_pressure=[np.nan] * 3,
    )
    result = result_1.copy()
    result.extend(result_2)

    assert result.rate_sm3_day == [[1, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2]]
