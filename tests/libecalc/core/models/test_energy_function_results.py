from copy import deepcopy
from datetime import datetime

import numpy as np

import libecalc.common.energy_usage_type
from libecalc.domain.process.compressor.dto import compressor_models as dto
from libecalc.common.units import Unit
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.compressor_consumer_function import (
    CompressorConsumerFunction,
)
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.core.results import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainResult,
    EnergyFunctionGenericResult,
)
from libecalc.expression import Expression


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
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )
    result_2 = CompressorTrainResult(
        energy_usage=[2.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult.create_empty(number_of_periods=3),
            CompressorStageResult.create_empty(number_of_periods=3),
        ],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )
    result_3 = CompressorTrainResult(
        energy_usage=[3.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[CompressorStageResult.create_empty(number_of_periods=3)],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )

    result_4 = CompressorTrainResult(
        energy_usage=[],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[],
        power_unit=Unit.MEGA_WATT,
        stage_results=[],
        rate_sm3_day=[],
        failure_status=[],
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )

    result = deepcopy(result_1)
    for temporal_result in [result_2, result_3, result_4]:
        result.extend(temporal_result)

    assert result.energy_usage == [1, 1, 1, 2, 2, 2, 3, 3, 3]
    assert len(result.stage_results) == 2
    for stage_result in result.stage_results:
        assert len(stage_result.energy_usage) == 9


def test_extend_compressor_train_results_over_temporal_models_with_none_variables():
    """Check if extending variables over several temporal models are ok.
    E.g. if first temporal model has None for a give variable, while the
    second model has values. Then, the extended results should contain correct
    number of values/timesteps, and include the real values of the second
    temporal model.
    :return:
    """

    compressor = CompressorModelSampled(
        data_transfer_object=dto.CompressorSampled(
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
            energy_usage_values=[0, 1],
            power_interpolation_values=[0.0, 1],
            rate_values=[0, 1],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )
    )

    variables_map = VariablesMap(
        time_vector=[datetime(2023, 1, 1), datetime(2024, 1, 1), datetime(2025, 1, 1)],
        variables={"SIM1;v1": [1, 1], "SIM1;v2": [1, 1]},
    )

    # Results 1: first temporal model - 2 timesteps.
    # Initially, before evaluate, mass_rate_kg_per_hr is None.
    result_1 = (
        CompressorConsumerFunction(
            compressor_function=compressor,
            rate_expression=Expression.setup_from_expression(1),
            suction_pressure_expression=Expression.setup_from_expression(20),
            discharge_pressure_expression=Expression.setup_from_expression(200),
            condition_expression=None,
            power_loss_factor_expression=None,
        )
        .evaluate(expression_evaluator=variables_map, regularity=[1] * variables_map.number_of_periods)
        .energy_function_result
    )

    stage_result_3 = CompressorStageResult.create_empty(number_of_periods=3)
    stage_result_3.mass_rate_kg_per_hr = [1, 1, 1]

    # Results 2: second temporal model - 3 timesteps. Has real values for mass_rate_kg_per_hr.
    result_2 = CompressorTrainResult(
        energy_usage=[0, 1.0, 1.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[stage_result_3],
        rate_sm3_day=[np.nan] * 3,
        failure_status=[None] * 3,
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )

    result = deepcopy(result_1)
    result.extend(result_2)

    # Ensure no data loss when first temporal model contains None for a variable:
    # Check that extended stage results for mass_rate_kg_per_hr not based only on first
    # temporal model, i.e. that the variable is not None
    assert result.stage_results[0].mass_rate_kg_per_hr is not None  # noqa

    # Ensure no data loss when first temporal model contains None for a variable:
    # Check that extended stage results for mass_rate_kg_per_hr contains correct number
    # of timestep values, and the real values of the third model - for mass_rate_kg_per_hr
    assert result.stage_results[0].mass_rate_kg_per_hr == [np.nan, np.nan, 1, 1, 1]  # noqa


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
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )
    result_2 = CompressorTrainResult(
        energy_usage=[2.0] * 3,
        energy_usage_unit=Unit.MEGA_WATT,
        power=[np.nan] * 3,
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult.create_empty(number_of_periods=3),
            CompressorStageResult.create_empty(number_of_periods=3),
        ],
        rate_sm3_day=[[2] * 3] * 3,
        failure_status=[None] * 3,
        inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
        outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=3),
    )
    result = deepcopy(result_1)
    result.extend(result_2)

    assert result.rate_sm3_day == [[1, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2]]
