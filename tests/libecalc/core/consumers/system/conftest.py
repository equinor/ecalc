from unittest.mock import Mock

import numpy as np
import pytest

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
    PumpSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    CompressorSystemOperationalSettingExpressions,
    PumpSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.process.core.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.core.results import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainResult,
    PumpModelResult,
)
from libecalc.domain.process.core.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.expression import Expression


def get_pump_system_mock_operational_expressions(
    number_of_periods: int, number_of_consumers: int
) -> list[PumpSystemOperationalSettingExpressions]:
    expression = PumpSystemOperationalSettingExpressions(
        rates=[Expression.setup_from_expression(1)] * number_of_consumers,
        suction_pressures=[Expression.setup_from_expression(1)] * number_of_consumers,
        discharge_pressures=[Expression.setup_from_expression(2)] * number_of_consumers,
        fluid_densities=[Expression.setup_from_expression(1)] * number_of_consumers,
    )
    return [expression] * number_of_periods


def get_compressor_system_mock_operational_expressions(
    number_of_periods: int, number_of_consumers: int
) -> list[CompressorSystemOperationalSettingExpressions]:
    expression = CompressorSystemOperationalSettingExpressions(
        rates=[Expression.setup_from_expression(1)] * number_of_consumers,
        suction_pressures=[Expression.setup_from_expression(1)] * number_of_consumers,
        discharge_pressures=[Expression.setup_from_expression(2)] * number_of_consumers,
    )
    return [expression] * number_of_periods


@pytest.fixture
def pump_system(pump_single_speed, pump_variable_speed) -> PumpSystemConsumerFunction:
    return PumpSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="pump1", facility_model=pump_single_speed),
            ConsumerSystemComponent(name="pump2", facility_model=pump_variable_speed),
        ],
        operational_settings_expressions=get_pump_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=2
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def compressor_system_single(compressor_model_sampled) -> CompressorSystemConsumerFunction:
    return CompressorSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="compressor1", facility_model=compressor_model_sampled),
        ],
        operational_settings_expressions=get_compressor_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=1
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def compressor_system_sampled(compressor_model_sampled) -> CompressorSystemConsumerFunction:
    return CompressorSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="compressor1", facility_model=compressor_model_sampled),
            ConsumerSystemComponent(name="compressor2", facility_model=compressor_model_sampled),
        ],
        operational_settings_expressions=get_compressor_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=2
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def compressor_system_sampled_2(compressor_model_sampled_2) -> CompressorSystemConsumerFunction:
    return CompressorSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="compressor1", facility_model=compressor_model_sampled_2),
            ConsumerSystemComponent(name="compressor2", facility_model=compressor_model_sampled_2),
        ],
        operational_settings_expressions=get_compressor_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=2
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def compressor_system_sampled_3d(compressor_model_sampled_3d) -> CompressorSystemConsumerFunction:
    return CompressorSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="compressor1", facility_model=compressor_model_sampled_3d),
            ConsumerSystemComponent(name="compressor2", facility_model=compressor_model_sampled_3d),
        ],
        operational_settings_expressions=get_compressor_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=2
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def compressor_system_sampled_mix(
    compressor_model_sampled, compressor_model_sampled_3d
) -> CompressorSystemConsumerFunction:
    return CompressorSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(name="compressor1d", facility_model=compressor_model_sampled),
            ConsumerSystemComponent(
                name="compressor_3d",
                facility_model=compressor_model_sampled_3d,
            ),
        ],
        operational_settings_expressions=get_compressor_system_mock_operational_expressions(
            number_of_periods=3, number_of_consumers=2
        ),
        condition_expression=None,
        power_loss_factor_expression=None,
    )


@pytest.fixture
def pump_model_result() -> PumpModelResult:
    return PumpModelResult(
        energy_usage=[1.0, 2.0, 3.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1.0, 2.0, 3.0],
        power_unit=Unit.MEGA_WATT,
        rate=[1.0, 2.0, 3.0],
        suction_pressure=[1.0, 2.0, 3.0],
        discharge_pressure=[1.0, 2.0, 3.0],
        fluid_density=[1.0, 2.0, 3.0],
        operational_head=[1000, 1000, 1000],
    )


@pytest.fixture
def pump_model_result_2() -> PumpModelResult:
    return PumpModelResult(
        energy_usage=[4.0, 5.0, 6.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[4.0, 5.0, 6.0],
        power_unit=Unit.MEGA_WATT,
        rate=[4.0, 5.0, 6.0],
        suction_pressure=[4.0, 5.0, 6.0],
        discharge_pressure=[4.0, 5.0, 6.0],
        fluid_density=[4.0, 5.0, 6.0],
    )


@pytest.fixture
def compressor_model_result() -> CompressorTrainResult:
    return CompressorTrainResult(
        energy_usage=[1.0, 2.0, 3.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1.0, 2.0, 3.0],
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult(
                energy_usage=[1.0, 2.0, 3.0],
                energy_usage_unit=Unit.MEGA_WATT,
                power=[1.0, 2.0, 3.0],
                power_unit=Unit.MEGA_WATT,
                inlet_stream_condition=CompressorStreamCondition(
                    actual_rate_m3_per_hr=[1.0, 2.0, 3.0], pressure=[1.0, 2.0, 3.0]
                ),
                outlet_stream_condition=CompressorStreamCondition(pressure=[1.0, 2.0, 3.0]),
                fluid_composition={},
                chart=None,
                is_valid=[True] * 3,
                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED] * 3,
                rate_has_recirculation=[False] * 3,
                rate_exceeds_maximum=[False] * 3,
                pressure_is_choked=[False] * 3,
                head_exceeds_maximum=[False] * 3,
                asv_recirculation_loss_mw=[0] * 3,
            ),
        ],
        rate_sm3_day=[np.nan, np.nan, np.nan],
        failure_status=[
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        ],
        inlet_stream_condition=CompressorStreamCondition(
            actual_rate_m3_per_hr=[1.0, 2.0, 3.0], pressure=[1.0, 2.0, 3.0]
        ),
        outlet_stream_condition=CompressorStreamCondition(pressure=[1.0, 2.0, 3.0]),
    )


@pytest.fixture
def compressor_model_result_invalid_steps() -> CompressorTrainResult:
    return CompressorTrainResult(
        energy_usage=[1.0, np.nan, 3.0],
        energy_usage_unit=Unit.MEGA_WATT,
        power=[1.0, np.nan, 3.0],
        power_unit=Unit.MEGA_WATT,
        stage_results=[
            CompressorStageResult(
                energy_usage=[1.0, np.nan, 3.0],
                energy_usage_unit=Unit.MEGA_WATT,
                power=[1.0, np.nan, 3.0],
                power_unit=Unit.MEGA_WATT,
                inlet_stream_condition=CompressorStreamCondition(
                    actual_rate_m3_per_hr=[1.0, 2.0, 3.0], pressure=[1.0, 2.0, 3.0]
                ),
                outlet_stream_condition=CompressorStreamCondition(pressure=[1.0, 2.0, 3.0]),
                fluid_composition={},
                chart=None,
                is_valid=[True] * 3,
                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED] * 3,
                rate_has_recirculation=[False] * 3,
                rate_exceeds_maximum=[False] * 3,
                pressure_is_choked=[False] * 3,
                head_exceeds_maximum=[False] * 3,
                asv_recirculation_loss_mw=[0, 0, 0],
            )
        ],
        rate_sm3_day=[np.nan, np.nan, np.nan],
        failure_status=[
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        ],
        inlet_stream_condition=CompressorStreamCondition(
            actual_rate_m3_per_hr=[1.0, 2.0, 3.0], pressure=[1.0, 2.0, 3.0]
        ),
        outlet_stream_condition=CompressorStreamCondition(pressure=[1.0, 2.0, 3.0]),
    )


@pytest.fixture
def consumer_system_result() -> ConsumerSystemConsumerFunctionResult:
    a = np.array([1, 2, 3])
    return ConsumerSystemConsumerFunctionResult(
        periods=Periods([Mock(Period)] * 3),
        is_valid=np.array([True, True, True]),
        energy_usage=a,
        energy_usage_before_power_loss_factor=a,
        condition=a,
        power_loss_factor=a,
        energy_function_result=None,
        power=a,
        operational_setting_used=np.array([0, 1, 2]),
        operational_settings=[[]],
        operational_settings_results=[[]],
        consumer_results=[[]],
        cross_over_used=None,
    )
