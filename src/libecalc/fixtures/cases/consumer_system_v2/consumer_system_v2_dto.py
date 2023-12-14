from datetime import datetime

import pytest

from libecalc import dto
from libecalc.common.string.string_utils import generate_id
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto import (
    CompressorSystemCompressor,
    CompressorSystemConsumerFunction,
    CompressorSystemOperationalSetting,
    PumpSystemConsumerFunction,
    PumpSystemOperationalSetting,
    PumpSystemPump,
)
from libecalc.dto.base import (
    ComponentType,
    ConsumerUserDefinedCategoryType,
    FuelTypeUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.dto.components import (
    Crossover,
    ExpressionStreamConditions,
    ExpressionTimeSeries,
    SystemComponentConditions,
)
from libecalc.dto.types import ConsumptionType, EnergyUsageType
from libecalc.expression import Expression
from libecalc.fixtures.case_types import DTOCase

regularity = {
    datetime(2022, 1, 1, 0, 0): Expression.setup_from_expression(1),
}
fuel = {
    datetime(2022, 1, 1, 0, 0): dto.FuelType(
        name="fuel_gas",
        user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS,
        emissions=[
            dto.Emission(
                factor=Expression.setup_from_expression(2.2),
                name="co2",
            )
        ],
    )
}

genset = dto.GeneratorSetSampled(
    headers=["POWER", "FUEL"],
    data=[
        [0.0, 0.1, 1000000.0],
        [0.0, 0.1, 1000000.0],
    ],
    energy_usage_adjustment_constant=0.0,
    energy_usage_adjustment_factor=1.0,
)
compressor_1d = dto.CompressorSampled(
    energy_usage_adjustment_constant=0.0,
    energy_usage_adjustment_factor=1.0,
    energy_usage_type=dto.types.EnergyUsageType.FUEL,
    energy_usage_values=[0.0, 10000.0, 11000.0, 12000.0, 13000.0],
    rate_values=[0.0, 1000000.0, 2000000.0, 3000000.0, 4000000.0],
    suction_pressure_values=None,
    discharge_pressure_values=None,
    power_interpolation_values=[0.0, 1.0, 2.0, 3.0, 4.0],
)

pump_model_single_speed = dto.PumpModel(
    energy_usage_adjustment_factor=1,
    energy_usage_adjustment_constant=0,
    chart=dto.SingleSpeedChart(
        rate_actual_m3_hour=[100, 200, 300, 400, 500],
        polytropic_head_joule_per_kg=[9810.0, 19620.0, 29430.0, 39240.0, 49050.0],
        efficiency_fraction=[0.4, 0.5, 0.75, 0.70, 0.60],
        speed_rpm=1,
    ),
    head_margin=0,
)

compressor1 = dto.components.CompressorComponent(
    name="compressor1",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    fuel=fuel,
    regularity=regularity,
    consumes=dto.types.ConsumptionType.FUEL,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
)
compressor2 = dto.components.CompressorComponent(
    name="compressor2",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    fuel=fuel,
    regularity=regularity,
    consumes=dto.types.ConsumptionType.FUEL,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
)
compressor3 = dto.components.CompressorComponent(
    name="compressor3",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    fuel=fuel,
    regularity=regularity,
    consumes=dto.types.ConsumptionType.FUEL,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
)
compressor4_temporal_model = dto.components.CompressorComponent(
    name="compressor3",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    fuel=fuel,
    regularity=regularity,
    consumes=dto.types.ConsumptionType.FUEL,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d, datetime(2024, 1, 1, 0, 0): compressor_1d},
)
compressor5_with_overlapping_temporal_model = dto.components.CompressorComponent(
    name="compressor3",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    fuel=fuel,
    regularity=regularity,
    consumes=dto.types.ConsumptionType.FUEL,
    energy_usage_model={
        datetime(2022, 1, 1, 0, 0): compressor_1d,
        datetime(2024, 1, 1, 0, 0): compressor_1d,
        datetime(2025, 1, 1, 0, 0): compressor_1d,
    },
)

pump1 = dto.components.PumpComponent(
    name="pump1",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
    regularity=regularity,
    consumes=dto.types.ConsumptionType.ELECTRICITY,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
)
pump2 = dto.components.PumpComponent(
    name="pump2",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
    regularity=regularity,
    consumes=dto.types.ConsumptionType.ELECTRICITY,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
)
pump3 = dto.components.PumpComponent(
    name="pump3",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
    regularity=regularity,
    consumes=dto.types.ConsumptionType.ELECTRICITY,
    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
)

compressor_system = dto.FuelConsumer(
    component_type=ComponentType.COMPRESSOR_SYSTEM,
    name="compressor_system",
    fuel=fuel,
    energy_usage_model={
        datetime(2022, 1, 1, 0, 0): CompressorSystemConsumerFunction(
            energy_usage_type=EnergyUsageType.FUEL,
            power_loss_factor=None,
            compressors=[
                CompressorSystemCompressor(
                    name="compressor1",
                    compressor_train=compressor_1d,
                ),
                CompressorSystemCompressor(
                    name="compressor2",
                    compressor_train=compressor_1d,
                ),
                CompressorSystemCompressor(
                    name="compressor3",
                    compressor_train=compressor_1d,
                ),
            ],
            total_system_rate=None,
            operational_settings=[
                CompressorSystemOperationalSetting(
                    rates=[Expression.setup_from_expression(x) for x in [1000000, 6000000, 6000000]],
                    suction_pressures=[Expression.setup_from_expression("50")] * 3,
                    discharge_pressures=[Expression.setup_from_expression("250")] * 3,
                    crossover=[0, 1, 1],
                ),
                CompressorSystemOperationalSetting(
                    rates=[Expression.setup_from_expression(x) for x in ["$var.compressor1", 5000000, 5000000]],
                    suction_pressures=[Expression.setup_from_expression("50")] * 3,
                    discharge_pressures=[Expression.setup_from_expression("125")] * 3,
                    crossover=[0, 1, 1],
                ),
                CompressorSystemOperationalSetting(
                    rates=[Expression.setup_from_expression(x) for x in [1000000, 5000000, 5000000]],
                    suction_pressures=[Expression.setup_from_expression("50")] * 3,
                    discharge_pressures=[Expression.setup_from_expression("125")] * 3,
                    crossover=[0, 1, 1],
                ),
            ],
        )
    },
    regularity=regularity,
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
)

compressor_system_v2 = dto.components.ConsumerSystem(
    name="compressor_system_v2",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR},
    regularity=regularity,
    consumes=ConsumptionType.FUEL,
    fuel=fuel,
    component_conditions=SystemComponentConditions(
        crossover=[
            Crossover(from_component_id=generate_id("compressor2"), to_component_id=generate_id("compressor1")),
            Crossover(from_component_id=generate_id("compressor3"), to_component_id=generate_id("compressor1")),
        ],
    ),
    stream_conditions_priorities={
        "pri1": {
            "compressor1": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=1000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor2": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=6000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor3": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=6000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
        },
        "pri2": {
            "compressor1": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value="$var.compressor1",
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor2": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=5000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor3": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=5000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
        },
        "pri3": {
            "compressor1": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=1000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor2": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=5000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "compressor3": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=5000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
        },
    },
    consumers=[
        compressor1,  # Max rate of 4000000
        compressor2,  # Max rate of 4000000
        compressor3,  # Max rate of 4000000
    ],
)

pump_system = dto.ElectricityConsumer(
    component_type=ComponentType.PUMP_SYSTEM,
    name="pump_system",
    energy_usage_model={
        datetime(2022, 1, 1, 0, 0): PumpSystemConsumerFunction(
            energy_usage_type=EnergyUsageType.POWER,
            condition=Expression.setup_from_expression("1"),
            power_loss_factor=Expression.setup_from_expression("0"),
            pumps=[
                PumpSystemPump(
                    name="pump1",
                    pump_model=pump_model_single_speed,
                ),
                PumpSystemPump(
                    name="pump2",
                    pump_model=pump_model_single_speed,
                ),
                PumpSystemPump(
                    name="pump3",
                    pump_model=pump_model_single_speed,
                ),
            ],
            total_system_rate=None,
            operational_settings=[
                PumpSystemOperationalSetting(
                    rates=[Expression.setup_from_expression(x) for x in [4000000, 5000000, 6000000]],
                    suction_pressures=[Expression.setup_from_expression("50")] * 3,
                    discharge_pressures=[Expression.setup_from_expression("250")] * 3,
                    crossover=[0, 1, 1],
                ),
                PumpSystemOperationalSetting(
                    rates=[Expression.setup_from_expression(x) for x in [2000000, 2500000, 3000000]],
                    suction_pressures=[Expression.setup_from_expression("50")] * 3,
                    discharge_pressures=[Expression.setup_from_expression("125")] * 3,
                    crossover=[0, 1, 1],
                ),
            ],
            fluid_density=Expression.setup_from_expression("2"),
        )
    },
    regularity=regularity,
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
)

pump_system_v2 = dto.components.ConsumerSystem(
    name="pump_system_v2",
    user_defined_category={datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
    regularity=regularity,
    consumes=dto.types.ConsumptionType.ELECTRICITY,
    component_conditions=SystemComponentConditions(
        crossover=[
            Crossover(from_component_id=generate_id("pump2"), to_component_id=generate_id("pump1")),
            Crossover(from_component_id=generate_id("pump3"), to_component_id=generate_id("pump1")),
        ],
    ),
    stream_conditions_priorities={
        "pri1": {
            "pump1": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=4000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "pump2": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=5000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "pump3": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=6000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=250,
                        unit=Unit.BARA,
                    ),
                ),
            },
        },
        "pri2": {
            "pump1": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=2000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "pump2": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=2500000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
            "pump3": {
                "inlet": ExpressionStreamConditions(
                    rate=ExpressionTimeSeries(
                        value=3000000,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                    pressure=ExpressionTimeSeries(
                        value=50,
                        unit=Unit.BARA,
                    ),
                    fluid_density=ExpressionTimeSeries(
                        value=2,
                        unit=Unit.KG_SM3,
                    ),
                ),
                "outlet": ExpressionStreamConditions(
                    pressure=ExpressionTimeSeries(
                        value=125,
                        unit=Unit.BARA,
                    ),
                ),
            },
        },
    },
    consumers=[pump1, pump2, pump3],
)


@pytest.fixture
def consumer_system_v2_dto_fixture() -> DTOCase:
    """
    In order to make fixtures easier to spot, we should mark/tag/name them in order
    to easily find them. Fixtures can e.g. not be used directly in parameterized test,
    so providing a wrapper for fixtures seems appropriate.
    :return:
    """
    return consumer_system_v2_dto()


def consumer_system_v2_dto() -> DTOCase:
    """
    Base Case consumer system v2 (no temporal models, no temporal operational settings)
    :return:
    """
    assert pump1
    assert pump2
    assert pump3
    return DTOCase(
        dto.Asset(
            component_type=ComponentType.ASSET,
            name="consumer_system_v2",
            installations=[
                dto.Installation(
                    name="installation",
                    user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                    component_type=ComponentType.INSTALLATION,
                    regularity=regularity,
                    hydrocarbon_export={datetime(2022, 1, 1, 0, 0): Expression.setup_from_expression(17)},
                    fuel_consumers=[
                        dto.GeneratorSet(
                            name="GeneratorSet",
                            user_defined_category={
                                datetime(2022, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                datetime(2022, 1, 1): genset,
                            },
                            regularity=regularity,
                            fuel=fuel,
                            consumers=[pump_system, pump_system_v2],
                        ),
                        compressor_system,
                        compressor_system_v2,
                    ],
                    venting_emitters=[],
                )
            ],
        ),
        variables=dto.VariablesMap(
            time_vector=[
                datetime(2022, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 0),
                datetime(2025, 1, 1, 0, 0),
                datetime(2026, 1, 1, 0, 0),
            ],
            variables={
                "compressor1;rate": [0.0, 0.0, 0.0, 4000000.0],
                "$var.compressor1": [0, 0, 0, 4000000],
            },
        ),
    )
