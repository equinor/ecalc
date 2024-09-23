from typing import List

import numpy as np

from libecalc.common.units import Unit
from libecalc.core.consumers.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSetting,
)
from libecalc.core.consumers.legacy_consumer.system.results import (
    ConsumerSystemComponentResult,
    ConsumerSystemOperationalSettingResult,
)
from libecalc.core.consumers.legacy_consumer.system.utils import (
    assemble_operational_setting_from_model_result_list,
    get_operational_settings_number_used_from_model_results,
)
from libecalc.core.models.chart.chart_area_flag import ChartAreaFlag
from libecalc.core.models.results import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainResult,
)


def test_calculate_system_energy_usage_from_operational_setting_one_option_success():
    operational_settings_results: List[ConsumerSystemOperationalSettingResult] = [
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="1",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[10],
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[1],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[10],
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[1],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[0],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        )
    ]

    operational_setting_used = get_operational_settings_number_used_from_model_results(
        consumer_system_operational_settings_results=operational_settings_results
    )

    assert operational_setting_used == np.array([0])


def test_calculate_system_energy_usage_from_operational_setting_one_option_failure():
    operational_settings_results: List[ConsumerSystemOperationalSettingResult] = [
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="1",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[
                            np.nan
                        ],  # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[np.nan],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[np.nan],
                                # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[np.nan],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[np.nan],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        )
    ]

    operational_setting_used = get_operational_settings_number_used_from_model_results(
        consumer_system_operational_settings_results=operational_settings_results
    )

    # The result is invalid with energy usage: NaN. We shall return the results from the last operational setting tested
    # In this case, it is [0].
    assert operational_setting_used == np.array([0])


def test_calculate_system_energy_usage_from_operational_setting_two_options_first_outside_capacity_second_within_capacity_and_chosen():
    operational_settings_results: List[ConsumerSystemOperationalSettingResult] = [
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="1",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[
                            np.nan
                        ],  # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[np.nan],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[np.nan],
                                # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[np.nan],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[0],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        ),
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="2",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[10],
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[1],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[10],
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[1],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[0],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        ),
    ]

    operational_setting_used = get_operational_settings_number_used_from_model_results(
        consumer_system_operational_settings_results=operational_settings_results
    )

    assert operational_setting_used == np.array([1])


def test_calculate_system_energy_usage_from_operational_setting_two_options_both_outside_capacity_but_second_chosen_as_no_other_options():
    operational_settings_results: List[ConsumerSystemOperationalSettingResult] = [
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="1",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[
                            np.nan
                        ],  # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[np.nan],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[np.nan],
                                # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[np.nan],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[0],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        ),
        ConsumerSystemOperationalSettingResult(
            consumer_results=[
                ConsumerSystemComponentResult(
                    name="2",
                    consumer_model_result=CompressorTrainResult(
                        energy_usage=[
                            np.nan
                        ],  # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        power=[np.nan],
                        power_unit=Unit.MEGA_WATT,
                        rate_sm3_day=[2],
                        turbine_result=None,
                        stage_results=[
                            CompressorStageResult(
                                energy_usage=[np.nan],
                                # NaN indicates that the combination of rate, Ps and Pd was not within operation area of this operational setting option
                                energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                power=[np.nan],
                                power_unit=Unit.MEGA_WATT,
                                is_valid=[True],
                                inlet_stream_condition=CompressorStreamCondition(),
                                outlet_stream_condition=CompressorStreamCondition(),
                                fluid_composition={},
                                chart_area_flags=[ChartAreaFlag.NOT_CALCULATED],
                                rate_has_recirculation=[False],
                                rate_exceeds_maximum=[False],
                                pressure_is_choked=[False],
                                head_exceeds_maximum=[False],
                                asv_recirculation_loss_mw=[0],
                            )
                        ],
                        failure_status=[None],
                        inlet_stream_condition=CompressorStreamCondition(),
                        outlet_stream_condition=CompressorStreamCondition(),
                    ),
                )
            ],
        ),
    ]

    operational_setting_used = get_operational_settings_number_used_from_model_results(
        consumer_system_operational_settings_results=operational_settings_results
    )

    # Two invalid settings results should return the last index as settings used.
    assert operational_setting_used == np.array([1])


def test_assemble_operational_setting_from_model_result_list():
    operational_settings = [
        ConsumerSystemOperationalSetting(
            rates=[np.array([0, 1, 2, 3, 4]), np.array([0, 1, 2, 3, 4])],
            suction_pressures=[np.array([0, 1, 2, 3, 4]), np.array([0, 1, 2, 3, 4])],
            discharge_pressures=[np.array([0, 1, 2, 3, 4]), np.array([0, 1, 2, 3, 4])],
            fluid_densities=[np.array([0, 1, 2, 3, 4]), np.array([0, 1, 2, 3, 4])],
        ),
        ConsumerSystemOperationalSetting(
            rates=[np.array([10, 11, 12, 13, 14]), np.array([10, 11, 12, 13, 14])],
            suction_pressures=[np.array([10, 11, 12, 13, 14]), np.array([10, 11, 12, 13, 14])],
            discharge_pressures=[np.array([10, 11, 12, 13, 14]), np.array([10, 11, 12, 13, 14])],
            fluid_densities=[np.array([10, 11, 12, 13, 14]), np.array([10, 11, 12, 13, 14])],
        ),
        ConsumerSystemOperationalSetting(
            rates=[np.array([20, 21, 22, 23, 24]), np.array([20, 21, 22, 23, 24])],
            suction_pressures=[np.array([20, 21, 22, 23, 24]), np.array([20, 21, 22, 23, 24])],
            discharge_pressures=[np.array([20, 21, 22, 23, 24]), np.array([20, 21, 22, 23, 24])],
            fluid_densities=[np.array([20, 21, 22, 23, 24]), np.array([20, 21, 22, 23, 24])],
        ),
        ConsumerSystemOperationalSetting(
            rates=[np.array([30, 31, 32, 33, 34]), np.array([30, 31, 32, 33, 34])],
            suction_pressures=[np.array([30, 31, 32, 33, 34]), np.array([30, 31, 32, 33, 34])],
            discharge_pressures=[np.array([30, 31, 32, 33, 34]), np.array([30, 31, 32, 33, 34])],
            fluid_densities=[np.array([30, 31, 32, 33, 34]), np.array([30, 31, 32, 33, 34])],
        ),
    ]

    setting_number_used_per_timestep = [0, 3, 2, 1, 0]

    result = assemble_operational_setting_from_model_result_list(
        operational_settings=operational_settings, setting_number_used_per_timestep=setting_number_used_per_timestep
    )

    assert result.rates[0].tolist() == [0, 31, 22, 13, 4]
    assert result.rates[1].tolist() == [0, 31, 22, 13, 4]
    assert result.suction_pressures[0].tolist() == [0, 31, 22, 13, 4]
    assert result.suction_pressures[1].tolist() == [0, 31, 22, 13, 4]
    assert result.discharge_pressures[0].tolist() == [0, 31, 22, 13, 4]
    assert result.discharge_pressures[1].tolist() == [0, 31, 22, 13, 4]
