from datetime import datetime

import pytest

from libecalc import dto
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto.base import (
    ComponentType,
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.expression import Expression
from libecalc.fixtures.case_types import DTOCase
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmission,
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
)


@pytest.fixture
def compressor_system_variable_speed_compressor_trains(
    fuel_gas,
    regularity,
    compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="compressor_system_variable_speed_compressor_trains",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        fuel=fuel_gas,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(2018, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="train1",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train2",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train3",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=50),
                        discharge_pressure=Expression.setup_from_expression(value=250),
                    )
                ],
            ),
            datetime(2019, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                power_loss_factor=Expression.setup_from_expression(value=0.0),
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="train1_upgraded",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train2_upgraded",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=50),
                        discharge_pressure=Expression.setup_from_expression(value=250),
                    )
                ],
            ),
        },
    )


@pytest.fixture
def compressor_system_variable_speed_compressor_trains_multiple_suction_discharge_pressures(
    fuel_gas,
    regularity,
    compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="compressor_system_variable_speed_compressor_trains_multiple_pressures",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        fuel=fuel_gas,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(2018, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="train1",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train2",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train3",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=20),
                            Expression.setup_from_expression(value=30),
                            Expression.setup_from_expression(value=40),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=220),
                            Expression.setup_from_expression(value=230),
                            Expression.setup_from_expression(value=240),
                        ],
                    ),
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 3"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 3"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 3"),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=50),
                            Expression.setup_from_expression(value=60),
                            Expression.setup_from_expression(value=70),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=250),
                            Expression.setup_from_expression(value=260),
                            Expression.setup_from_expression(value=270),
                        ],
                    ),
                ],
            ),
            datetime(2019, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                power_loss_factor=Expression.setup_from_expression(value=0.0),
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="train1_upgraded",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                    dto.CompressorSystemCompressor(
                        name="train2_upgraded",
                        compressor_train=compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=40),
                            Expression.setup_from_expression(value=45),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=240),
                            Expression.setup_from_expression(value=245),
                        ],
                    )
                ],
            ),
        },
    )


@pytest.fixture
def simplified_compressor_train_predefined_variable_speed_charts_with_gerg_fluid(
    simplified_variable_speed_compressor_train_with_gerg_fluid2,
    regularity,
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="simplified_compressor_train_predefined_variable_speed_charts_with_gerg_fluid",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                model=simplified_variable_speed_compressor_train_with_gerg_fluid2,
            ),
        },
    )


@pytest.fixture
def tabulated(fuel_gas, regularity) -> dto.FuelConsumer:
    tabulated = dto.TabulatedConsumerFunction(
        model=dto.TabulatedData(
            headers=["VARIABLE1", "FUEL"],
            data=[[0.0, 20000.0, 40000.0, 60000.0, 80000.0], [0.0, 1000.0, 2000.0, 3000.0, 4000.0]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        ),
        variables=[dto.Variables(name="VARIABLE1", expression=Expression.setup_from_expression(value="SIM1;GAS_LIFT"))],
        energy_usage_type=dto.types.EnergyUsageType.FUEL,
    )
    return dto.FuelConsumer(
        name="tabulated",
        component_type=ComponentType.GENERIC,
        fuel=fuel_gas,
        energy_usage_model={datetime(1900, 1, 1): tabulated},
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
        regularity=regularity,
    )


@pytest.fixture
def compressor(compressor_sampled_1d, fuel_gas, regularity) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="single_1d_compressor_sampled",
        component_type=ComponentType.COMPRESSOR,
        fuel=fuel_gas,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                model=compressor_sampled_1d,
                rate_standard_m3_day=Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                suction_pressure=Expression.setup_from_expression(value=200),
                discharge_pressure=Expression.setup_from_expression(value=400),
            )
        },
    )


@pytest.fixture
def pump_system_el_consumer(single_speed_pump, regularity) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="waterinj",
        component_type=ComponentType.PUMP_SYSTEM,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.PumpSystemConsumerFunction(
                condition=Expression.setup_from_expression(value="SIM1;WATER_PROD >0"),
                pumps=[
                    dto.PumpSystemPump(name="pump1", pump_model=single_speed_pump),
                    dto.PumpSystemPump(name="pump2", pump_model=single_speed_pump),
                ],
                fluid_density=Expression.setup_from_expression(value="1026"),
                total_system_rate=Expression.setup_from_expression(value="SIM1;WATER_INJ"),
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                operational_settings=[
                    dto.PumpSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=1),
                            Expression.setup_from_expression(value=0),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=3),
                            Expression.setup_from_expression(value=3),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=200),
                            Expression.setup_from_expression(value=200),
                        ],
                        crossover=[2, 0],
                    ),
                    dto.PumpSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=0.5),
                            Expression.setup_from_expression(value=0.5),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=3),
                        discharge_pressure=Expression.setup_from_expression(value=200),
                    ),
                ],
            ),
        },
    )


@pytest.fixture
def simplified_variable_speed_compressor_train_known_stages_consumer(
    simplified_variable_speed_compressor_train_known_stages,
    regularity,
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="simplified_variable_speed_compressor_train_known_stages_consumer",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                model=simplified_variable_speed_compressor_train_known_stages,
            )
        },
    )


@pytest.fixture
def simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model(
    simplified_variable_speed_compressor_train_known_stages,
    regularity,
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(2018, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                model=simplified_variable_speed_compressor_train_known_stages,
            ),
            datetime(2019, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=40),
                discharge_pressure=Expression.setup_from_expression(value=260),
                model=simplified_variable_speed_compressor_train_known_stages,
            ),
        },
    )


@pytest.fixture
def generic_from_design_point_compressor_train_consumer(
    medium_fluid_dto,
    regularity,
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="generic_from_design_point_compressor_train_consumer",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                condition=Expression.setup_from_expression("1 > 0"),
                model=dto.CompressorTrainSimplifiedWithUnknownStages(
                    fluid_model=medium_fluid_dto,
                    stage=dto.CompressorStage(
                        compressor_chart=dto.GenericChartFromDesignPoint(
                            polytropic_efficiency_fraction=0.75,
                            design_rate_actual_m3_per_hour=5000,
                            design_polytropic_head_J_per_kg=100000,
                        ),
                        inlet_temperature_kelvin=303.15,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                    ),
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                    maximum_pressure_ratio_per_stage=3.5,
                ),
                power_loss_factor=Expression.setup_from_expression(value=0.05),
            )
        },
    )


@pytest.fixture
def simplified_variable_speed_compressor_train_unknown_stages_consumer(
    medium_fluid_dto, regularity
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="simplified_variable_speed_compressor_train_unknown_stages_consumer",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                model=dto.CompressorTrainSimplifiedWithUnknownStages(
                    fluid_model=medium_fluid_dto,
                    stage=dto.CompressorStage(
                        compressor_chart=dto.GenericChartFromInput(
                            polytropic_efficiency_fraction=0.75,
                        ),
                        inlet_temperature_kelvin=303.15,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                    ),
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                    maximum_pressure_ratio_per_stage=3.5,
                ),
            )
        },
    )


@pytest.fixture
def turbine_driven_compressor_train(fuel_gas, compressor_with_turbine, regularity):
    return dto.FuelConsumer(
        name="turbine_driven_compressor_train",
        component_type=ComponentType.COMPRESSOR,
        fuel=fuel_gas,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=30),
                discharge_pressure=Expression.setup_from_expression(value=200),
                model=compressor_with_turbine,
            ),
        },
    )


@pytest.fixture
def compressor_system(fuel_gas, compressor_sampled_1d, regularity) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="sampled_compressor_system",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        fuel=fuel_gas,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorSystemConsumerFunction(
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="sampled_train1",
                        compressor_train=compressor_sampled_1d,
                    ),
                    dto.CompressorSystemCompressor(
                        name="sampled_train2",
                        compressor_train=compressor_sampled_1d,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {/} 2"),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=200),
                        discharge_pressure=Expression.setup_from_expression(value=400),
                    ),
                ],
            ),
        },
    )


@pytest.fixture
def simplified_compressor_system(
    fuel_gas,
    simplified_variable_speed_compressor_train_known_stages,
    regularity,
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="simplified_compressor_system",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorSystemConsumerFunction(
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                compressors=[
                    dto.CompressorSystemCompressor(
                        name="simplified_train1",
                        compressor_train=simplified_variable_speed_compressor_train_known_stages,
                    ),
                    dto.CompressorSystemCompressor(
                        name="simplified_train2",
                        compressor_train=simplified_variable_speed_compressor_train_known_stages,
                    ),
                ],
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rates=[
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {*} 3"),
                            Expression.setup_from_expression(value="SIM1;GAS_PROD {*} 3"),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=100),
                        discharge_pressure=Expression.setup_from_expression(value=400),
                    ),
                ],
            ),
        },
    )


@pytest.fixture
def deh(regularity) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="deh",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=4.1),
                condition=Expression.setup_from_expression(value="SIM1;GAS_LIFT > 0"),
                power_loss_factor=Expression.setup_from_expression(value=0.05),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                consumption_rate_type=RateType.STREAM_DAY,
            ),
        },
    )


@pytest.fixture
def late_start_consumer(regularity) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="late_start_consumer",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        regularity=regularity,
        energy_usage_model={
            datetime(2018, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=1),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
            ),
            datetime(2019, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=2),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
            ),
            datetime(2020, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=0),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
            ),
        },
    )


@pytest.fixture
def late_start_consumer_evolving_type(regularity) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="late_start_consumer_evolving_type",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
        regularity=regularity,
        energy_usage_model={
            datetime(2018, 1, 1): dto.TabulatedConsumerFunction(
                model=dto.TabulatedData(
                    headers=["RATE", "POWER"],
                    data=[
                        [0, 1, 8500, 9000, 17000, 17500, 36000, 72000, 142000],
                        [0, 4.5, 4.5, 4.61, 6.37, 9.11, 13.18, 26.360, 52.720],
                    ],
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                ),
                variables=[
                    dto.Variables(
                        name="RATE",
                        expression=Expression.setup_from_expression(value="$var.salt_water_injection"),
                    )
                ],
                energy_usage_type=dto.types.EnergyUsageType.POWER,
            ),
        },
    )


@pytest.fixture
def salt_water_injection_tabular(regularity) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="salt_water_injection_tabular",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.TabulatedConsumerFunction(
                model=dto.TabulatedData(
                    headers=["RATE", "POWER"],
                    data=[
                        [0, 1, 8500, 9000, 17000, 17500, 36000, 72000, 142000],
                        [0, 4.5, 4.5, 4.61, 6.37, 9.11, 13.18, 26.360, 52.720],
                    ],
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                ),
                variables=[
                    dto.Variables(
                        name="RATE",
                        expression=Expression.setup_from_expression(value="$var.salt_water_injection"),
                    )
                ],
                energy_usage_type=dto.types.EnergyUsageType.POWER,
            ),
        },
    )


@pytest.fixture
def water_injection_single_speed(regularity, single_speed_pump) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="water_injection_single_speed",
        component_type=ComponentType.PUMP,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.PumpConsumerFunction(
                condition=Expression.setup_from_expression(value="SIM1;GAS_PROD > 0"),
                model=single_speed_pump,
                power_loss_factor=None,
                rate_standard_m3_day=Expression.setup_from_expression(value="SIM1;WATER_INJ"),
                suction_pressure=Expression.setup_from_expression(value=3),
                discharge_pressure=Expression.setup_from_expression(value=200),
                fluid_density=Expression.setup_from_expression(value=1000),
            ),
        },
    )


@pytest.fixture
def water_injection_variable_speed(regularity, variable_speed_pump) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="water_injection_variable_speed",
        component_type=ComponentType.PUMP,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.PumpConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                model=variable_speed_pump,
                rate_standard_m3_day=Expression.setup_from_expression(value="SIM1;WATER_INJ"),
                suction_pressure=Expression.setup_from_expression(value=3),
                discharge_pressure=Expression.setup_from_expression(value=20),
                fluid_density=Expression.setup_from_expression(value=1000),
                condition=Expression.setup_from_expression(value="SIM1;GAS_LIFT > 0"),
                power_loss_factor=Expression.setup_from_expression(value="SIM1;POWERLOSS_CONSTANT {+} 0.05"),
            ),
        },
    )


@pytest.fixture
def variable_speed_compressor_train_predefined_charts(
    regularity, medium_fluid_dto, predefined_variable_speed_compressor_chart_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="variable_speed_compressor_train_predefined_charts",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5000000),
                suction_pressure=Expression.setup_from_expression(value=50),
                discharge_pressure=Expression.setup_from_expression(value=250),
                model=dto.VariableSpeedCompressorTrain(
                    fluid_model=medium_fluid_dto,
                    stages=[
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0.1,
                        ),
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                    ],
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                    pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
                ),
            )
        },
    )


@pytest.fixture
def single_speed_compressor_train_asv_pressure_control(
    regularity, medium_fluid_dto, user_defined_single_speed_compressor_chart_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="single_speed_compressor_train_asv_pressure_control",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5800000.0),
                suction_pressure=Expression.setup_from_expression(value=80.0),
                discharge_pressure=Expression.setup_from_expression(value=300.0),
                model=dto.SingleSpeedCompressorTrain(
                    fluid_model=medium_fluid_dto,
                    stages=[
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                    ],
                    pressure_control=dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                ),
            )
        },
    )


@pytest.fixture
def single_speed_compressor_train_upstream_choke_pressure_control(
    regularity, medium_fluid_dto, user_defined_single_speed_compressor_chart_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="single_speed_compressor_train_upstream_choke_pressure_control",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5800000.0),
                suction_pressure=Expression.setup_from_expression(value=80.0),
                discharge_pressure=Expression.setup_from_expression(value=300.0),
                model=dto.SingleSpeedCompressorTrain(
                    fluid_model=medium_fluid_dto,
                    stages=[
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                    ],
                    pressure_control=dto.types.FixedSpeedPressureControl.UPSTREAM_CHOKE,
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                ),
            )
        },
    )


@pytest.fixture
def single_speed_compressor_train_downstream_choke_pressure_control(
    regularity, medium_fluid_dto, user_defined_single_speed_compressor_chart_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="single_speed_compressor_train_downstream_choke_pressure_control",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=5800000.0),
                suction_pressure=Expression.setup_from_expression(value=80.0),
                discharge_pressure=Expression.setup_from_expression(value=300.0),
                model=dto.SingleSpeedCompressorTrain(
                    fluid_model=medium_fluid_dto,
                    stages=[
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                    ],
                    pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                ),
            )
        },
    )


@pytest.fixture
def single_speed_compressor_train_downstream_choke_pressure_control_maximum_discharge_pressure(
    regularity, medium_fluid_dto, user_defined_single_speed_compressor_chart_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="single_speed_compressor_train_downstream_choke_pressure_control_maximum_discharge_pressure",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                rate_standard_m3_day=Expression.setup_from_expression(value=1000000.0),
                suction_pressure=Expression.setup_from_expression(value=80.0),
                discharge_pressure=Expression.setup_from_expression(value=300.0),
                model=dto.SingleSpeedCompressorTrain(
                    fluid_model=medium_fluid_dto,
                    stages=[
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                        dto.CompressorStage(
                            inlet_temperature_kelvin=303.15,
                            compressor_chart=user_defined_single_speed_compressor_chart_dto,
                            remove_liquid_after_cooling=True,
                            pressure_drop_before_stage=0,
                            control_margin=0,
                        ),
                    ],
                    pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
                    maximum_discharge_pressure=350.0,
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                ),
            )
        },
    )


@pytest.fixture
def variable_speed_compressor_train_multiple_input_streams_and_interstage_pressure(
    regularity, predefined_variable_speed_compressor_chart_dto, rich_fluid_dto, medium_fluid_dto
) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="variable_speed_compressor_train_multiple_input_streams_and_interstage_pressure",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity=regularity,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                model=dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures(
                    stages=[
                        dto.MultipleStreamsCompressorStage(
                            inlet_temperature_kelvin=303.15,
                            remove_liquid_after_cooling=True,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            stream_reference=["in_stream_stage_1"],
                            pressure_drop_before_stage=0.0,
                            control_margin=0,
                        ),
                        dto.MultipleStreamsCompressorStage(
                            inlet_temperature_kelvin=303.15,
                            remove_liquid_after_cooling=True,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            stream_reference=["in_stream_stage_2", "another_in_stream_stage_2"],
                            pressure_drop_before_stage=0.0,
                            control_margin=0,
                        ),
                        dto.MultipleStreamsCompressorStage(
                            inlet_temperature_kelvin=303.15,
                            remove_liquid_after_cooling=True,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            pressure_drop_before_stage=0.0,
                            control_margin=0,
                        ),
                        dto.MultipleStreamsCompressorStage(
                            inlet_temperature_kelvin=303.15,
                            remove_liquid_after_cooling=True,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            stream_reference=["out_stream_stage_4_export"],
                            interstage_pressure_control=dto.InterstagePressureControl(
                                downstream_pressure_control=dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
                                upstream_pressure_control=dto.types.FixedSpeedPressureControl.UPSTREAM_CHOKE,
                            ),
                            pressure_drop_before_stage=0.0,
                            control_margin=0,
                        ),
                        dto.MultipleStreamsCompressorStage(
                            inlet_temperature_kelvin=303.15,
                            remove_liquid_after_cooling=True,
                            compressor_chart=predefined_variable_speed_compressor_chart_dto,
                            pressure_drop_before_stage=0.0,
                            control_margin=0,
                        ),
                    ],
                    streams=[
                        dto.MultipleStreamsAndPressureStream(
                            fluid_model=rich_fluid_dto,
                            name="in_stream_stage_1",
                            typ=dto.types.FluidStreamType.INGOING,
                        ),
                        dto.MultipleStreamsAndPressureStream(
                            fluid_model=medium_fluid_dto,
                            name="in_stream_stage_2",
                            typ=dto.types.FluidStreamType.INGOING,
                        ),
                        dto.MultipleStreamsAndPressureStream(
                            fluid_model=medium_fluid_dto,
                            name="another_in_stream_stage_2",
                            typ=dto.types.FluidStreamType.INGOING,
                        ),
                        dto.MultipleStreamsAndPressureStream(
                            name="out_stream_stage_4_export",
                            typ=dto.types.FluidStreamType.OUTGOING,
                        ),
                    ],
                    energy_usage_adjustment_constant=1.0,
                    energy_usage_adjustment_factor=1.0,
                    pressure_control=dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
                ),
                discharge_pressure=Expression.setup_from_expression(value=600),
                suction_pressure=Expression.setup_from_expression(value=10),
                rate_standard_m3_day=[
                    Expression.setup_from_expression(value=900000),
                    Expression.setup_from_expression(value=250000),
                    Expression.setup_from_expression(value=250000),
                    Expression.setup_from_expression(value=1000000),
                ],
                interstage_control_pressure=Expression.setup_from_expression(value=90),
                power_loss_factor=Expression.setup_from_expression(value=0.05),
            )
        },
    )


@pytest.fixture
def methane_venting(regularity) -> YamlVentingEmitter:
    return YamlVentingEmitter(
        name="methane_venting",
        category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
        emission=YamlVentingEmission(
            name="CH4",
            rate=YamlEmissionRate(value="FLARE;METHANE_RATE", unit=Unit.KILO_PER_DAY, type=RateType.STREAM_DAY),
        ),
    )


@pytest.fixture
def flare(fuel_gas, regularity) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="flare",
        component_type=ComponentType.GENERIC,
        fuel=fuel_gas,
        energy_usage_model={
            datetime(1900, 1, 1): dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="FLARE;FLARE_RATE"),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                consumption_rate_type=RateType.STREAM_DAY,
            )
        },
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FLARE},
        regularity=regularity,
    )


@pytest.fixture
def genset_sampled() -> dto.GeneratorSetSampled:
    return dto.GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[
            [0.0, 0.1, 10.0, 20.0, 21.0, 40.0, 100.0, 1000.0],
            [0.0, 75000.0, 75000.0, 120000.0, 150000.0, 256840.0, 1000000.0, 1000000.0],
        ],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def all_energy_usage_models_dto(
    regularity,
    fuel_gas,
    genset_sampled,
    generic_from_design_point_compressor_train_consumer,
    simplified_variable_speed_compressor_train_known_stages_consumer,
    simplified_variable_speed_compressor_train_unknown_stages_consumer,
    deh,
    late_start_consumer,
    late_start_consumer_evolving_type,
    salt_water_injection_tabular,
    water_injection_single_speed,
    water_injection_variable_speed,
    pump_system_el_consumer,
    simplified_compressor_system,
    simplified_compressor_train_predefined_variable_speed_charts_with_gerg_fluid,
    variable_speed_compressor_train_predefined_charts,
    single_speed_compressor_train_asv_pressure_control,
    single_speed_compressor_train_upstream_choke_pressure_control,
    single_speed_compressor_train_downstream_choke_pressure_control,
    single_speed_compressor_train_downstream_choke_pressure_control_maximum_discharge_pressure,
    variable_speed_compressor_train_multiple_input_streams_and_interstage_pressure,
    compressor,
    tabulated,
    compressor_system,
    turbine_driven_compressor_train,
    compressor_system_variable_speed_compressor_trains,
    methane_venting,
    flare,
    all_energy_usage_models_variables,
) -> DTOCase:
    return DTOCase(
        dto.Asset(
            name="all_energy_usage_models",
            installations=[
                dto.Installation(
                    user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                    name="MAIN_INSTALLATION",
                    regularity=regularity,
                    hydrocarbon_export={
                        datetime(1900, 1, 1): Expression.setup_from_expression(
                            value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
                        ),
                    },
                    fuel_consumers=[
                        dto.GeneratorSet(
                            name="GeneratorSet",
                            user_defined_category={
                                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                datetime(1900, 1, 1): genset_sampled,
                                datetime(2018, 1, 1): genset_sampled,
                            },
                            regularity=regularity,
                            fuel=fuel_gas,
                            consumers=[
                                generic_from_design_point_compressor_train_consumer,
                                simplified_variable_speed_compressor_train_known_stages_consumer,
                                simplified_variable_speed_compressor_train_unknown_stages_consumer,
                                deh,
                                late_start_consumer,
                                late_start_consumer_evolving_type,
                                salt_water_injection_tabular,
                                water_injection_single_speed,
                                water_injection_variable_speed,
                                pump_system_el_consumer,
                                simplified_compressor_system,
                                simplified_compressor_train_predefined_variable_speed_charts_with_gerg_fluid,
                                variable_speed_compressor_train_predefined_charts,
                                single_speed_compressor_train_asv_pressure_control,
                                single_speed_compressor_train_upstream_choke_pressure_control,
                                single_speed_compressor_train_downstream_choke_pressure_control,
                                single_speed_compressor_train_downstream_choke_pressure_control_maximum_discharge_pressure,
                                variable_speed_compressor_train_multiple_input_streams_and_interstage_pressure,
                            ],
                        ),
                        flare,
                        compressor,
                        tabulated,
                        compressor_system,
                        turbine_driven_compressor_train,
                        compressor_system_variable_speed_compressor_trains,
                    ],
                    venting_emitters=[
                        methane_venting,
                    ],
                )
            ],
        ),
        all_energy_usage_models_variables,
    )


@pytest.fixture
def compressor_systems_and_compressor_train_temporal_dto(
    regularity,
    fuel_gas,
    genset_sampled,
    simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model,
    compressor_system_variable_speed_compressor_trains_multiple_suction_discharge_pressures,
    all_energy_usage_models_variables,
) -> DTOCase:
    return DTOCase(
        dto.Asset(
            name="all_energy_usage_models",
            installations=[
                dto.Installation(
                    user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                    name="MAIN_INSTALLATION",
                    regularity=regularity,
                    hydrocarbon_export={
                        datetime(1900, 1, 1): Expression.setup_from_expression(
                            value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
                        ),
                    },
                    fuel_consumers=[
                        dto.GeneratorSet(
                            name="GeneratorSet",
                            user_defined_category={
                                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                datetime(1900, 1, 1): genset_sampled,
                                datetime(2018, 1, 1): genset_sampled,
                            },
                            regularity=regularity,
                            fuel=fuel_gas,
                            consumers=[
                                simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model,
                            ],
                        ),
                        compressor_system_variable_speed_compressor_trains_multiple_suction_discharge_pressures,
                    ],
                )
            ],
        ),
        all_energy_usage_models_variables,
    )
