from copy import deepcopy
from datetime import datetime

import pytest
from libecalc import dto
from libecalc.dto.base import (
    ComponentType,
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.expression import Expression
from libecalc.fixtures.case_types import DTOCase


def direct_consumer(power: float) -> dto.DirectConsumerFunction:
    return dto.DirectConsumerFunction(
        load=Expression.setup_from_expression(value=power),
        energy_usage_type=dto.types.EnergyUsageType.POWER,
    )


def generator_set_sampled_300mw() -> dto.GeneratorSetSampled:
    return dto.GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[[0, 1, 300], [0, 1, 300]],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def tabulated_energy_usage_model() -> dto.TabulatedConsumerFunction:
    return dto.TabulatedConsumerFunction(
        model=dto.TabulatedData(
            headers=["RATE", "FUEL"],
            data=[[0, 1, 2, 10000], [0, 2, 4, 5]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        ),
        variables=[dto.Variables(name="RATE", expression=Expression.setup_from_expression(value="RATE"))],
        energy_usage_type=dto.types.EnergyUsageType.FUEL,
    )


def tabulated_fuel_consumer_with_time_slots(fuel_gas) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="fuel_consumer_with_time_slots",
        component_type=ComponentType.GENERIC,
        fuel=fuel_gas,
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={
            datetime(1900, 1, 1): tabulated_energy_usage_model(),
            datetime(2019, 1, 1): tabulated_energy_usage_model(),
        },
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
    )


def single_speed_compressor_chart() -> dto.SingleSpeedChart:
    """A simple single speed compressor chart."""
    return dto.SingleSpeedChart(
        rate_actual_m3_hour=[x * 1000 for x in range(1, 11)],  # 1000 -> 10 000
        polytropic_head_joule_per_kg=[100000 - (x * 10000) for x in range(10)],  # 100 000 -> 10 000
        efficiency_fraction=[round(1 - (x / 10), 1) for x in range(10)],  # 1 -> 0.1
        speed_rpm=1,
    )


@pytest.fixture
def single_speed_compressor_train(medium_fluid_dto) -> dto.SingleSpeedCompressorTrain:
    return dto.SingleSpeedCompressorTrain(
        fluid_model=medium_fluid_dto,
        stages=[
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=single_speed_compressor_chart(),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=single_speed_compressor_chart(),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
        ],
        pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        maximum_discharge_pressure=350.0,
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def simple_compressor_model(single_speed_compressor_train) -> dto.CompressorConsumerFunction:
    return dto.CompressorConsumerFunction(
        energy_usage_type=dto.types.EnergyUsageType.POWER,
        rate_standard_m3_day=Expression.setup_from_expression(value="RATE"),
        suction_pressure=Expression.setup_from_expression(value=20),
        discharge_pressure=Expression.setup_from_expression(value=200),
        model=single_speed_compressor_train,
    )


@pytest.fixture
def time_slot_electricity_consumer_with_changing_model_type(simple_compressor_model) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="el-consumer1",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={
            # Starting with a direct consumer because we don't know everything in the past
            datetime(2017, 1, 1): direct_consumer(power=5),
            # Then we know some more. So we model it as a simplified model
            datetime(2018, 1, 1): simple_compressor_model,
            # Finally we decommission the equipment by setting direct consumer to zero load.
            datetime(2024, 1, 1): direct_consumer(power=0),
        },
    )


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="el-consumer2",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={
            datetime(2017, 1, 1): direct_consumer(power=5),
            datetime(2019, 1, 1): direct_consumer(power=10),
            datetime(2024, 1, 1): direct_consumer(power=0),
        },
    )


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type2() -> dto.ElectricityConsumer:
    """Same consumer as 'time_slot_electricity_consumer_with_same_model_type', different name,
    used in the second generator set.
    """
    return dto.ElectricityConsumer(
        name="el-consumer4",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={
            datetime(2017, 1, 1): direct_consumer(power=5),
            datetime(2019, 1, 1): direct_consumer(power=10),
            datetime(2024, 1, 1): direct_consumer(power=0),
        },
    )


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type3(simple_compressor_model) -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="el-consumer-simple-compressor-model-with-timeslots",
        component_type=ComponentType.COMPRESSOR,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={
            datetime(2017, 1, 1): simple_compressor_model,
            datetime(2019, 1, 1): simple_compressor_model,
            datetime(2024, 1, 1): simple_compressor_model,
        },
    )


@pytest.fixture
def time_slot_electricity_consumer_too_late_startup() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="el-consumer3",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
        energy_usage_model={datetime(2050, 1, 1): direct_consumer(power=5)},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
    )


@pytest.fixture
def time_slots_simplified_compressor_system(
    fuel_gas,
    single_speed_compressor_train,
) -> dto.ElectricityConsumer:
    """Here we model a compressor system that changes over time. New part is suffixed "_upgrade"."""
    energy_usage_model = dto.CompressorSystemConsumerFunction(
        energy_usage_type=dto.types.EnergyUsageType.POWER,
        compressors=[
            dto.CompressorSystemCompressor(
                name="train1",
                compressor_train=single_speed_compressor_train,
            ),
            dto.CompressorSystemCompressor(
                name="train2",
                compressor_train=single_speed_compressor_train,
            ),
        ],
        operational_settings=[
            dto.CompressorSystemOperationalSetting(
                rate_fractions=[Expression.setup_from_expression(value=1), Expression.setup_from_expression(value=0)],
                suction_pressure=Expression.setup_from_expression(value=41),
                discharge_pressure=Expression.setup_from_expression(value=200),
            ),
            dto.CompressorSystemOperationalSetting(
                rate_fractions=[
                    Expression.setup_from_expression(value=0.5),
                    Expression.setup_from_expression(value=0.5),
                ],
                suction_pressure=Expression.setup_from_expression(value=41),
                discharge_pressure=Expression.setup_from_expression(value=200),
            ),
        ],
        total_system_rate=Expression.setup_from_expression(value="RATE"),
    )

    energy_usage_model_upgrade = deepcopy(energy_usage_model)
    energy_usage_model_upgrade.compressors[0].name = "train1_upgrade"
    energy_usage_model_upgrade.compressors[1].name = "train2_upgrade"
    return dto.ElectricityConsumer(
        name="simplified_compressor_system",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
        energy_usage_model={datetime(1900, 1, 1): energy_usage_model, datetime(2019, 1, 1): energy_usage_model_upgrade},
    )


@pytest.fixture
def consumer_with_time_slots_models_dto(
    fuel_gas,
    time_slot_electricity_consumer_with_changing_model_type,
    time_slot_electricity_consumer_with_same_model_type,
    time_slot_electricity_consumer_with_same_model_type2,
    time_slot_electricity_consumer_with_same_model_type3,
    time_slot_electricity_consumer_too_late_startup,
    time_slots_simplified_compressor_system,
) -> DTOCase:
    start_year = 2010
    number_of_years = 20
    time_vector = [datetime(year, 1, 1) for year in range(start_year, start_year + number_of_years)]

    return DTOCase(
        ecalc_model=dto.Asset(
            name="time_slots_model",
            installations=[
                dto.Installation(
                    user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                    name="some_installation",
                    regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
                    hydrocarbon_export={
                        datetime(1900, 1, 1): Expression.setup_from_expression(value="RATE"),
                    },
                    fuel_consumers=[
                        dto.GeneratorSet(
                            name="some_genset",
                            user_defined_category={
                                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                datetime(1900, 1, 1): generator_set_sampled_300mw(),
                            },
                            fuel=fuel_gas,
                            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
                            consumers=[
                                time_slot_electricity_consumer_with_changing_model_type,
                                time_slot_electricity_consumer_with_same_model_type,
                                time_slot_electricity_consumer_with_same_model_type3,
                                time_slot_electricity_consumer_too_late_startup,
                                time_slots_simplified_compressor_system,
                            ],
                        ),
                        dto.GeneratorSet(
                            name="some_genset_startup_after_consumer",
                            user_defined_category={
                                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                # 2 years after the consumers start.
                                datetime(2019, 1, 1): generator_set_sampled_300mw(),
                            },
                            fuel=fuel_gas,
                            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(value=1)},
                            consumers=[time_slot_electricity_consumer_with_same_model_type2],
                        ),
                        tabulated_fuel_consumer_with_time_slots(fuel_gas),
                    ],
                    direct_emitters=[],
                )
            ],
        ),
        variables=dto.VariablesMap(time_vector=time_vector, variables={"RATE": [5000] * number_of_years}),
    )
