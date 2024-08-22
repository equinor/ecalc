import pytest

from libecalc.common.units import Unit
from libecalc.core.models.results.base import EnergyFunctionResult
from libecalc.core.models.results.compressor import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainResult,
)
from libecalc.dto.types import ChartAreaFlag


@pytest.fixture
def model_result() -> EnergyFunctionResult:
    return EnergyFunctionResult(
        energy_usage=[1, 2, 3],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1, 2, 3],
        power_unit=Unit.MEGA_WATT,
    )


@pytest.fixture
def compressor_model_result() -> CompressorTrainResult:
    return CompressorTrainResult(
        energy_usage=[1, 2, 3],
        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        power=[1, 2, 3],
        power_unit=Unit.MEGA_WATT,
        rate_sm3_day=[1, 2, 3],
        turbine_result=None,
        failure_status=[None, None, None],
        stage_results=[
            CompressorStageResult(
                energy_usage=[1, 2, 3],
                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                power=[1, 2, 3],
                power_unit=Unit.MEGA_WATT,
                is_valid=[True, True, False],
                inlet_stream_condition=CompressorStreamCondition(pressure=[10, 20, 30]),
                outlet_stream_condition=CompressorStreamCondition(pressure=[100, 200, 300]),
                fluid_composition={},
                chart_area_flags=[
                    ChartAreaFlag.INTERNAL_POINT,
                    ChartAreaFlag.INTERNAL_POINT,
                    ChartAreaFlag.INTERNAL_POINT,
                ],
                rate_has_recirculation=[True, True, False],
                rate_exceeds_maximum=[True, True, False],
                pressure_is_choked=[True, True, False],
                head_exceeds_maximum=[True, True, False],
                asv_recirculation_loss_mw=[0, 0, 0],
            ),
            CompressorStageResult(
                energy_usage=[4, 5, 6],
                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                power=[4, 5, 6],
                power_unit=Unit.MEGA_WATT,
                is_valid=[True, True, False],
                inlet_stream_condition=CompressorStreamCondition(pressure=[10, 20, 30]),
                outlet_stream_condition=CompressorStreamCondition(pressure=[100, 200, 300]),
                fluid_composition={},
                chart_area_flags=[
                    ChartAreaFlag.INTERNAL_POINT,
                    ChartAreaFlag.INTERNAL_POINT,
                    ChartAreaFlag.INTERNAL_POINT,
                ],
                rate_has_recirculation=[True, True, False],
                rate_exceeds_maximum=[True, True, False],
                pressure_is_choked=[True, True, False],
                head_exceeds_maximum=[True, True, False],
                asv_recirculation_loss_mw=[0, 0, 0],
            ),
        ],
    )


def test_extend_base_model(model_result):
    model_result.extend(model_result)

    assert model_result.energy_usage == [1, 2, 3] * 2
    assert model_result.power == [1, 2, 3] * 2
    assert model_result.energy_usage_unit == Unit.MEGA_WATT
    assert model_result.power_unit == Unit.MEGA_WATT


def test_extend_compressor_model_result(compressor_model_result):
    compressor_model_result.extend(compressor_model_result)

    assert compressor_model_result.energy_usage == [1, 2, 3] * 2
    assert compressor_model_result.power == [1, 2, 3] * 2
    assert compressor_model_result.energy_usage_unit == Unit.STANDARD_CUBIC_METER_PER_DAY
    assert compressor_model_result.power_unit == Unit.MEGA_WATT
    assert compressor_model_result.turbine_result is None
    assert compressor_model_result.failure_status == [None] * 6
    assert compressor_model_result.rate_sm3_day == [1, 2, 3] * 2

    assert compressor_model_result.stage_results[0].energy_usage == [1, 2, 3] * 2
    assert compressor_model_result.stage_results[1].energy_usage == [4, 5, 6] * 2

    assert compressor_model_result.stage_results[0].is_valid == [True, True, False] * 2
    assert compressor_model_result.stage_results[1].is_valid == [True, True, False] * 2

    assert compressor_model_result.stage_results[0].chart_area_flags == [ChartAreaFlag.INTERNAL_POINT] * 6
    assert compressor_model_result.stage_results[1].chart_area_flags == [ChartAreaFlag.INTERNAL_POINT] * 6

    assert compressor_model_result.stage_results[0].inlet_stream_condition.pressure == [10, 20, 30] * 2
    assert compressor_model_result.stage_results[1].inlet_stream_condition.pressure == [10, 20, 30] * 2

    assert compressor_model_result.stage_results[0].outlet_stream_condition.pressure == [100, 200, 300] * 2
    assert compressor_model_result.stage_results[1].outlet_stream_condition.pressure == [100, 200, 300] * 2
