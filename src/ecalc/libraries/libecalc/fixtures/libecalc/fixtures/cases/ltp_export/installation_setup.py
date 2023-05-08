from datetime import datetime
from typing import Dict

from libecalc import dto
from libecalc.common.time_utils import calculate_delta_days
from libecalc.common.units import Unit
from libecalc.dto.base import (
    ConsumerUserDefinedCategoryType,
)
from libecalc.expression import Expression

regularity_installation = 1.0
regularity_consumer = 1.0
power_usage_mw = 10

power_offshore_wind_mw = 1
power_compressor_mw = 3
compressor_rate = 3000000
fuel_rate = 67000
diesel_rate = 120000
co2_factor = 1
ch4_factor = 0.1

regularity_temporal_installation = {datetime(1900, 1, 1): Expression.setup_from_expression(regularity_installation)}
regularity_temporal_consumer = {datetime(1900, 1, 1): Expression.setup_from_expression(regularity_consumer)}

days1_first_half = calculate_delta_days([datetime(2027, 1, 1), datetime(2027, 4, 10)])
days2_first_half = calculate_delta_days([datetime(2028, 1, 1), datetime(2028, 4, 10)])

days1_second_half = calculate_delta_days([datetime(2027, 4, 10), datetime(2028, 1, 1)])
days2_second_half = calculate_delta_days([datetime(2028, 4, 10), datetime(2029, 1, 1)])


def fuel_turbine() -> dto.types.FuelType:
    return dto.types.FuelType(
        name="fuel_gas",
        price=Expression.setup_from_expression(value=10),
        emissions=[
            dto.Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
                tax=Expression.setup_from_expression(value=1),
            )
        ],
        user_defined_category=dto.types.FuelTypeUserDefinedCategoryType.FUEL_GAS,
    )


def diesel_turbine() -> dto.types.FuelType:
    return dto.types.FuelType(
        name="diesel",
        price=Expression.setup_from_expression(value=10000),
        emissions=[
            dto.Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
                tax=Expression.setup_from_expression(value=1),
            )
        ],
        user_defined_category=dto.types.FuelTypeUserDefinedCategoryType.DIESEL,
    )


def diesel_turbine_ch4() -> dto.types.FuelType:
    return dto.types.FuelType(
        name="diesel",
        price=Expression.setup_from_expression(value=10000),
        emissions=[
            dto.Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
                tax=Expression.setup_from_expression(value=1),
            ),
            dto.Emission(
                name="ch4",
                factor=Expression.setup_from_expression(value=ch4_factor),
                tax=Expression.setup_from_expression(value=1),
            ),
        ],
        user_defined_category=dto.types.FuelTypeUserDefinedCategoryType.DIESEL,
    )


def generator_set_fuel() -> dto.GeneratorSetSampled:
    return dto.GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[[0, 2.5, 5, power_usage_mw, 15, 20], [0, 30000, 45000, fuel_rate, 87000, 110000]],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def generator_set_diesel() -> dto.GeneratorSetSampled:
    return dto.GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[[0, power_usage_mw, 15, 20], [0, diesel_rate, 145000, 160000]],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def fuel_dict() -> Dict[datetime, dto.types.FuelType]:
    return {
        datetime(2027, 1, 1): diesel_turbine(),
        datetime(2027, 4, 10): fuel_turbine(),
        datetime(2028, 1, 1): diesel_turbine(),
        datetime(2028, 4, 10): fuel_turbine(),
        datetime(2029, 1, 1): diesel_turbine(),
    }


def fuel_dict_ch4() -> Dict[datetime, dto.types.FuelType]:
    return {
        datetime(2027, 1, 1): diesel_turbine_ch4(),
        datetime(2027, 4, 10): fuel_turbine(),
        datetime(2028, 1, 1): diesel_turbine_ch4(),
        datetime(2028, 4, 10): fuel_turbine(),
        datetime(2029, 1, 1): diesel_turbine_ch4(),
    }


def generator_set_dict() -> Dict[datetime, dto.GeneratorSetSampled]:
    return {
        datetime(2027, 1, 1): generator_set_diesel(),
        datetime(2027, 4, 10): generator_set_fuel(),
        datetime(2028, 1, 1): generator_set_diesel(),
        datetime(2028, 4, 10): generator_set_fuel(),
        datetime(2029, 1, 1): generator_set_diesel(),
    }


def category_dict() -> Dict[datetime, ConsumerUserDefinedCategoryType]:
    return {
        datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        datetime(2027, 4, 10): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        datetime(2028, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        datetime(2028, 4, 10): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        datetime(2029, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
    }


def category_dict_coarse() -> Dict[datetime, ConsumerUserDefinedCategoryType]:
    return {
        datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        datetime(2027, 4, 10): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        datetime(2028, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
    }


def direct_consumer(power: float) -> dto.DirectConsumerFunction:
    return dto.DirectConsumerFunction(
        load=Expression.setup_from_expression(value=power),
        energy_usage_type=dto.types.EnergyUsageType.POWER,
    )


def offshore_wind() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="direct_consumer",
        component_type=dto.base.ComponentType.GENERIC,
        user_defined_category={
            datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            datetime(2027, 4, 10): ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
            datetime(2028, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            datetime(2028, 4, 10): ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
            datetime(2029, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
        },
        energy_usage_model={
            datetime(2027, 1, 1): direct_consumer(power=0),
            datetime(2027, 4, 10): direct_consumer(power=power_offshore_wind_mw),
            datetime(2028, 1, 1): direct_consumer(power=0),
            datetime(2028, 4, 10): direct_consumer(power=power_offshore_wind_mw),
            datetime(2029, 1, 1): direct_consumer(power=0),
        },
        regularity=regularity_temporal_consumer,
    )


def no_el_consumption() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="no_el_consumption",
        component_type=dto.base.ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={datetime(2027, 1, 1): direct_consumer(power=0)},
        regularity=regularity_temporal_consumer,
    )


def simple_direct_el_consumer() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="direct_consumer",
        component_type=dto.base.ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={
            datetime(2027, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=power_usage_mw),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                consumption_rate_type=dto.types.RateType.STREAM_DAY,
            ),
        },
        regularity=regularity_temporal_consumer,
    )


def simple_direct_el_consumer_mobile() -> dto.ElectricityConsumer:
    return dto.ElectricityConsumer(
        name="direct_consumer_mobile",
        component_type=dto.base.ComponentType.GENERIC,
        user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={
            datetime(2027, 1, 1): dto.DirectConsumerFunction(
                load=Expression.setup_from_expression(value=power_usage_mw),
                energy_usage_type=dto.types.EnergyUsageType.POWER,
                consumption_rate_type=dto.types.RateType.STREAM_DAY,
            ),
        },
        regularity=regularity_temporal_consumer,
    )


def compressor_sampled():
    return dto.CompressorSampled(
        energy_usage_type=dto.types.EnergyUsageType.FUEL,
        energy_usage_values=[0, 10000, 11000, 12000, 13000],
        power_interpolation_values=[0.0, 1.0, 2.0, power_compressor_mw, 4.0],
        rate_values=[0, 1000000, 2000000, compressor_rate, 4000000],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def boiler_heater() -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="boiler",
        component_type=dto.base.ComponentType.DIRECT_EMITTER,
        fuel={datetime(2027, 1, 1): fuel_turbine()},
        user_defined_category={
            datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.BOILER,
            datetime(2028, 4, 10): ConsumerUserDefinedCategoryType.HEATER,
        },
        regularity=regularity_temporal_consumer,
        energy_usage_model={
            datetime(1900, 1, 1): dto.DirectConsumerFunction(
                fuel_rate=fuel_rate,
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
            )
        },
    )


def compressor() -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="single_1d_compressor_sampled",
        component_type=dto.base.ComponentType.COMPRESSOR,
        fuel={datetime(2027, 1, 1): fuel_turbine()},
        user_defined_category={
            datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            datetime(2027, 4, 10): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
            datetime(2028, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            datetime(2028, 4, 10): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
            datetime(2029, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
        },
        regularity=regularity_temporal_consumer,
        energy_usage_model={
            datetime(1900, 1, 1): dto.CompressorConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                model=compressor_sampled(),
                rate_standard_m3_day=Expression.setup_from_expression(value=compressor_rate),
                suction_pressure=Expression.setup_from_expression(value=200),
                discharge_pressure=Expression.setup_from_expression(value=400),
            )
        },
    )


def generator_set_direct_consumer_temporal_model() -> dto.GeneratorSet:
    return dto.GeneratorSet(
        name="genset",
        user_defined_category=category_dict_coarse(),
        fuel=fuel_dict(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_offshore_wind_temporal_model() -> dto.GeneratorSet:
    return dto.GeneratorSet(
        name="genset",
        user_defined_category={datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
        fuel={datetime(2027, 1, 1): fuel_turbine()},
        generator_set_model={datetime(2027, 1, 1): generator_set_fuel()},
        consumers=[offshore_wind()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_compressor_temporal_model() -> dto.GeneratorSet:
    return dto.GeneratorSet(
        name="genset",
        user_defined_category={datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
        fuel={datetime(2027, 1, 1): fuel_turbine()},
        generator_set_model={datetime(2027, 1, 1): generator_set_fuel()},
        consumers=[no_el_consumption()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_fixed_ch4_diesel() -> dto.GeneratorSet:
    return dto.GeneratorSet(
        name="genset_fixed",
        user_defined_category=category_dict(),
        fuel=fuel_dict_ch4(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_mobile_ch4_diesel() -> dto.GeneratorSet:
    return dto.GeneratorSet(
        name="genset_mobile",
        user_defined_category=category_dict(),
        fuel=fuel_dict_ch4(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer_mobile()],
        regularity=regularity_temporal_consumer,
    )


def expected_fuel_consumption():
    consumption = float(fuel_rate * days2_second_half * regularity_consumer)
    return consumption


def expected_diesel_consumption():
    consumption = float(diesel_rate * (days1_first_half + days2_first_half) * regularity_consumer)
    return consumption


def expected_pfs_el_consumption():
    consumption_mw_per_day = power_usage_mw * days1_second_half * regularity_consumer
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_gas_turbine_el_generated():
    consumption_mw_per_day = (
        power_usage_mw * (days1_first_half + days2_first_half + days2_second_half) * regularity_consumer
    )
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_co2_from_fuel():
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    emission_tons = float(emission_tons_per_day * days2_second_half * regularity_consumer)
    return emission_tons


def expected_co2_from_diesel():
    emission_kg_per_day = float(diesel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    emission_tons = float(emission_tons_per_day * (days1_first_half + days2_first_half) * regularity_consumer)
    return emission_tons


def expected_ch4_from_diesel():
    emission_kg_per_day = float(diesel_rate * ch4_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    emission_tons = float(emission_tons_per_day * (days1_first_half + days2_first_half) * regularity_consumer)
    return emission_tons


def expected_offshore_wind_el_consumption():
    consumption_mw_per_day = power_offshore_wind_mw * (days1_second_half + days2_second_half) * regularity_consumer
    consumption = -float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


# Why is this the only one without regularity?
def expected_gas_turbine_compressor_el_consumption():
    consumption_mw_per_day = power_compressor_mw * (days1_second_half + days2_second_half)
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_boiler_fuel_consumption():
    consumption = float(fuel_rate * (days1_first_half + days1_second_half + days2_first_half) * regularity_consumer)
    return consumption


def expected_heater_fuel_consumption():
    consumption = float(fuel_rate * days2_second_half * regularity_consumer)
    return consumption


def expected_co2_from_boiler():
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    emission_tons = float(
        emission_tons_per_day * (days1_first_half + days1_second_half + days2_first_half) * regularity_consumer
    )
    return emission_tons


def expected_co2_from_heater():
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    emission_tons = float(emission_tons_per_day * days2_second_half * regularity_consumer)
    return emission_tons


def installation_direct_consumer_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_direct_consumer_temporal_model()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.FIXED,
    )


def installation_offshore_wind_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_offshore_wind_temporal_model()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.FIXED,
    )


def installation_compressor_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_compressor_temporal_model(), compressor()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.FIXED,
    )


def installation_diesel_fixed_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_FIXED",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_fixed_ch4_diesel()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.FIXED,
    )


def installation_diesel_mobile_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_MOBILE",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_mobile_ch4_diesel()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.MOBILE,
    )


def installation_boiler_heater_dto() -> dto.Installation:
    return dto.Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[boiler_heater()],
        user_defined_category=dto.base.InstallationUserDefinedCategoryType.FIXED,
    )
