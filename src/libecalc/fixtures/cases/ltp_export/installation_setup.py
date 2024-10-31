from datetime import datetime

import numpy as np

import libecalc.common.component_type
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto import (
    CompressorConsumerFunction,
    CompressorSampled,
    DirectConsumerFunction,
    ElectricityConsumer,
    Emission,
    FuelConsumer,
    FuelType,
    GeneratorSet,
    GeneratorSetSampled,
    Installation,
)
from libecalc.dto.types import (
    ConsumerUserDefinedCategoryType,
    FuelTypeUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
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
nox_factor = 0.5
nmvoc_factor = 0

date1 = datetime(2027, 1, 1)
date2 = datetime(2027, 4, 10)
date3 = datetime(2028, 1, 1)
date4 = datetime(2028, 4, 10)
date5 = datetime(2029, 1, 1)

period1 = Period(date1, date2)
period2 = Period(date2, date3)
period3 = Period(date3, date4)
period4 = Period(date4, date5)
period5 = Period(date5)

full_period = Period(datetime(1900, 1, 1))
period_from_date1 = Period(date1)
period_from_date3 = Period(date3)

regularity_temporal_installation = {full_period: Expression.setup_from_expression(regularity_installation)}
regularity_temporal_consumer = {full_period: Expression.setup_from_expression(regularity_consumer)}

days_year1_first_half = period1.duration.days
days_year2_first_half = period3.duration.days

days_year1_second_half = period2.duration.days
days_year2_second_half = period4.duration.days


def fuel_turbine() -> FuelType:
    return FuelType(
        name="fuel_gas",
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
            )
        ],
        user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS,
    )


def diesel_turbine() -> FuelType:
    return FuelType(
        name="diesel",
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
            )
        ],
        user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
    )


def diesel_turbine_multi() -> FuelType:
    return FuelType(
        name="diesel",
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
            ),
            Emission(
                name="ch4",
                factor=Expression.setup_from_expression(value=ch4_factor),
            ),
            Emission(
                name="nox",
                factor=Expression.setup_from_expression(value=nox_factor),
            ),
            Emission(
                name="nmvoc",
                factor=Expression.setup_from_expression(value=nmvoc_factor),
            ),
        ],
        user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL,
    )


def generator_set_fuel() -> GeneratorSetSampled:
    return GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[[0, 2.5, 5, power_usage_mw, 15, 20], [0, 30000, 45000, fuel_rate, 87000, 110000]],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def generator_set_diesel() -> GeneratorSetSampled:
    return GeneratorSetSampled(
        headers=["POWER", "FUEL"],
        data=[[0, power_usage_mw, 15, 20], [0, diesel_rate, 145000, 160000]],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def fuel_dict() -> dict[Period, FuelType]:
    return {
        period1: diesel_turbine(),
        period2: fuel_turbine(),
        period3: diesel_turbine(),
        period4: fuel_turbine(),
        period5: diesel_turbine(),
    }


def fuel_dict_multi() -> dict[Period, FuelType]:
    return {
        period1: diesel_turbine_multi(),
        period2: fuel_turbine(),
        period3: diesel_turbine_multi(),
        period4: fuel_turbine(),
        period5: diesel_turbine_multi(),
    }


def generator_set_dict() -> dict[Period, GeneratorSetSampled]:
    return {
        period1: generator_set_diesel(),
        period2: generator_set_fuel(),
        period3: generator_set_diesel(),
        period4: generator_set_fuel(),
        period5: generator_set_diesel(),
    }


def category_dict() -> dict[Period, ConsumerUserDefinedCategoryType]:
    return {
        period1: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        period2: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        period3: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        period4: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        period5: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
    }


def category_dict_coarse() -> dict[Period, ConsumerUserDefinedCategoryType]:
    return {
        period1: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        period2: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        period_from_date3: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
    }


def direct_consumer(power: float) -> DirectConsumerFunction:
    return DirectConsumerFunction(
        load=Expression.setup_from_expression(value=power),
        energy_usage_type=EnergyUsageType.POWER,
    )


def offshore_wind() -> ElectricityConsumer:
    return ElectricityConsumer(
        name="direct_consumer",
        component_type=libecalc.common.component_type.ComponentType.GENERIC,
        user_defined_category={
            period1: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            period2: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
            period3: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            period4: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
            period5: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
        },
        energy_usage_model={
            period1: direct_consumer(power=0),
            period2: direct_consumer(power=power_offshore_wind_mw),
            period3: direct_consumer(power=0),
            period4: direct_consumer(power=power_offshore_wind_mw),
            period5: direct_consumer(power=0),
        },
        regularity=regularity_temporal_consumer,
    )


def no_el_consumption() -> ElectricityConsumer:
    return ElectricityConsumer(
        name="no_el_consumption",
        component_type=libecalc.common.component_type.ComponentType.GENERIC,
        user_defined_category={full_period: ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={period_from_date1: direct_consumer(power=0)},
        regularity=regularity_temporal_consumer,
    )


def simple_direct_el_consumer(name: str = "direct_consumer") -> ElectricityConsumer:
    return ElectricityConsumer(
        name=name,
        component_type=libecalc.common.component_type.ComponentType.GENERIC,
        user_defined_category={full_period: ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={
            period_from_date1: DirectConsumerFunction(
                load=Expression.setup_from_expression(value=power_usage_mw),
                energy_usage_type=EnergyUsageType.POWER,
                consumption_rate_type=RateType.STREAM_DAY,
            ),
        },
        regularity=regularity_temporal_consumer,
    )


def simple_direct_el_consumer_mobile() -> ElectricityConsumer:
    return ElectricityConsumer(
        name="direct_consumer_mobile",
        component_type=libecalc.common.component_type.ComponentType.GENERIC,
        user_defined_category={full_period: ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
        energy_usage_model={
            period_from_date1: DirectConsumerFunction(
                load=Expression.setup_from_expression(value=power_usage_mw),
                energy_usage_type=EnergyUsageType.POWER,
                consumption_rate_type=RateType.STREAM_DAY,
            ),
        },
        regularity=regularity_temporal_consumer,
    )


def compressor_sampled():
    return CompressorSampled(
        energy_usage_type=EnergyUsageType.FUEL,
        energy_usage_values=[0, 10000, 11000, 12000, 13000],
        power_interpolation_values=[0.0, 1.0, 2.0, power_compressor_mw, 4.0],
        rate_values=[0, 1000000, 2000000, compressor_rate, 4000000],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def boiler_heater() -> FuelConsumer:
    return FuelConsumer(
        name="boiler",
        component_type=libecalc.common.component_type.ComponentType.GENERIC,
        fuel={period_from_date1: fuel_turbine()},
        user_defined_category={
            Period(date1, date4): ConsumerUserDefinedCategoryType.BOILER,
            Period(date4): ConsumerUserDefinedCategoryType.HEATER,
        },
        regularity=regularity_temporal_consumer,
        energy_usage_model={
            full_period: DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value=fuel_rate),
                energy_usage_type=EnergyUsageType.FUEL,
            )
        },
    )


def compressor(name: str = "single_1d_compressor_sampled") -> FuelConsumer:
    return FuelConsumer(
        name=name,
        component_type=libecalc.common.component_type.ComponentType.COMPRESSOR,
        fuel={period_from_date1: fuel_turbine()},
        user_defined_category={
            period1: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            period2: ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
            period3: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            period4: ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
            period5: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
        },
        regularity=regularity_temporal_consumer,
        energy_usage_model={
            full_period: CompressorConsumerFunction(
                energy_usage_type=EnergyUsageType.FUEL,
                model=compressor_sampled(),
                rate_standard_m3_day=Expression.setup_from_expression(value=compressor_rate),
                suction_pressure=Expression.setup_from_expression(value=200),
                discharge_pressure=Expression.setup_from_expression(value=400),
            )
        },
    )


def generator_set_direct_consumer_temporal_model() -> GeneratorSet:
    return GeneratorSet(
        name="genset",
        user_defined_category=category_dict_coarse(),
        fuel=fuel_dict(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_offshore_wind_temporal_model() -> GeneratorSet:
    return GeneratorSet(
        name="genset",
        user_defined_category={period_from_date1: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
        fuel={period_from_date1: fuel_turbine()},
        generator_set_model={period_from_date1: generator_set_fuel()},
        consumers=[offshore_wind()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_compressor_temporal_model(consumers: list[ElectricityConsumer], name: str = "genset") -> GeneratorSet:
    return GeneratorSet(
        name=name,
        user_defined_category={period_from_date1: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
        fuel={period_from_date1: fuel_turbine()},
        generator_set_model={period_from_date1: generator_set_fuel()},
        consumers=consumers,
        regularity=regularity_temporal_consumer,
    )


def generator_set_fixed_diesel() -> GeneratorSet:
    return GeneratorSet(
        name="genset_fixed",
        user_defined_category=category_dict(),
        fuel=fuel_dict_multi(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer()],
        regularity=regularity_temporal_consumer,
    )


def generator_set_mobile_diesel() -> GeneratorSet:
    return GeneratorSet(
        name="genset_mobile",
        user_defined_category=category_dict(),
        fuel=fuel_dict_multi(),
        generator_set_model=generator_set_dict(),
        consumers=[simple_direct_el_consumer_mobile()],
        regularity=regularity_temporal_consumer,
    )


def expected_fuel_consumption() -> float:
    n_days = np.sum(days_year2_second_half)
    consumption = float(fuel_rate * n_days * regularity_consumer)
    return consumption


def expected_diesel_consumption() -> float:
    n_days = np.sum([days_year1_first_half, days_year2_first_half])
    consumption = float(diesel_rate * n_days * regularity_consumer)
    return consumption


def expected_pfs_el_consumption() -> float:
    n_days = np.sum(days_year1_second_half)
    consumption_mw_per_day = power_usage_mw * n_days * regularity_consumer
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_gas_turbine_el_generated() -> float:
    n_days = np.sum([(days_year1_first_half + days_year2_first_half + days_year2_second_half)])
    consumption_mw_per_day = power_usage_mw * n_days * regularity_consumer
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_co2_from_fuel() -> float:
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum(days_year2_second_half)
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_co2_from_diesel() -> float:
    emission_kg_per_day = float(diesel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_ch4_from_diesel() -> float:
    emission_kg_per_day = float(diesel_rate * ch4_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_nox_from_diesel() -> float:
    emission_kg_per_day = float(diesel_rate * nox_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_nmvoc_from_diesel() -> float:
    emission_kg_per_day = float(diesel_rate * nmvoc_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_offshore_wind_el_consumption() -> float:
    n_days = np.sum([days_year1_second_half, days_year2_second_half])
    consumption_mw_per_day = power_offshore_wind_mw * n_days * regularity_consumer
    consumption = -float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


# Why is this the only one without regularity?
def expected_gas_turbine_compressor_el_consumption() -> float:
    n_days = np.sum([days_year1_second_half, days_year2_second_half])
    consumption_mw_per_day = power_compressor_mw * n_days
    consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
    return consumption


def expected_boiler_fuel_consumption() -> float:
    n_days = np.sum([days_year1_first_half, days_year1_second_half, days_year2_first_half])
    consumption = float(fuel_rate * n_days * regularity_consumer)
    return consumption


def expected_heater_fuel_consumption() -> float:
    n_days = np.sum(days_year2_second_half)
    consumption = float(fuel_rate * n_days * regularity_consumer)
    return consumption


def expected_co2_from_boiler() -> float:
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year1_second_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_co2_from_heater() -> float:
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum(days_year2_second_half)
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def installation_direct_consumer_dto() -> Installation:
    return Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_direct_consumer_temporal_model()],
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
    )


def installation_offshore_wind_dto() -> Installation:
    return Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_offshore_wind_temporal_model()],
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
    )


def installation_compressor_dto(
    el_consumers: list[ElectricityConsumer],
    installation_name: str = "INSTALLATION_A",
    genset_name: str = "genset",
    compressor_name: str = "compressor",
) -> Installation:
    return Installation(
        name=installation_name,
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression(0)},
        fuel_consumers=[
            generator_set_compressor_temporal_model(el_consumers, name=genset_name),
            compressor(name=compressor_name),
        ],
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
    )


def installation_diesel_fixed_dto() -> Installation:
    return Installation(
        name="INSTALLATION_FIXED",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_fixed_diesel()],
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
    )


def installation_diesel_mobile_dto() -> Installation:
    return Installation(
        name="INSTALLATION_MOBILE",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[generator_set_mobile_diesel()],
        user_defined_category=InstallationUserDefinedCategoryType.MOBILE,
    )


def installation_boiler_heater_dto() -> Installation:
    return Installation(
        name="INSTALLATION_A",
        regularity=regularity_temporal_installation,
        hydrocarbon_export={full_period: Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[boiler_heater()],
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
    )
