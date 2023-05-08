from datetime import datetime

import pytest
from libecalc import dto
from libecalc.dto.base import ComponentType
from libecalc.expression import Expression
from libecalc.fixtures.case_types import DTOCase


@pytest.fixture
def consumer_system_v2_dto() -> DTOCase:
    regularity = {
        datetime(2022, 1, 1, 0, 0): Expression.setup_from_expression(1),
    }
    fuel = {
        datetime(2022, 1, 1, 0, 0): dto.FuelType(
            name="fuel_gas",
            price=Expression.setup_from_expression(1.5),
            user_defined_category="FUEL-GAS",
            emissions=[
                dto.Emission(
                    factor=Expression.setup_from_expression(2.2),
                    name="co2",
                    quota=None,
                    tax=Expression.setup_from_expression(1.51),
                )
            ],
        )
    }
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
    return DTOCase(
        dto.Asset(
            component_type=ComponentType.ASSET,
            name="consumer_system_v2",
            installations=[
                dto.Installation(
                    name="installation",
                    regularity=regularity,
                    hydrocarbon_export={datetime(2022, 1, 1, 0, 0): Expression.setup_from_expression(17)},
                    fuel_consumers=[
                        dto.components.CompressorSystem(
                            name="compressor_system_v2",
                            user_defined_category={datetime(2022, 1, 1): "COMPRESSOR"},
                            regularity=regularity,
                            consumes=dto.types.ConsumptionType.FUEL,
                            operational_settings={
                                datetime(2022, 1, 1, 0, 0): [
                                    dto.components.CompressorSystemOperationalSetting(
                                        rates=[
                                            Expression.setup_from_expression(x) for x in [1000000, 5000000, 6000000]
                                        ],
                                        inlet_pressures=[Expression.setup_from_expression("50")] * 3,
                                        outlet_pressures=[Expression.setup_from_expression("250")] * 3,
                                        crossover=[0, 1, 1],
                                    )
                                ]
                            },
                            compressors=[
                                dto.components.CompressorComponent(
                                    name="compressor1",
                                    user_defined_category={datetime(2022, 1, 1): "COMPRESSOR"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
                                    fuel=fuel,
                                ),
                                dto.components.CompressorComponent(
                                    name="compressor2",
                                    user_defined_category={datetime(2022, 1, 1): "COMPRESSOR"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
                                    fuel=fuel,
                                ),
                                dto.components.CompressorComponent(
                                    name="compressor3",
                                    user_defined_category={datetime(2022, 1, 1): "COMPRESSOR"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): compressor_1d},
                                    fuel=fuel,
                                ),
                            ],
                        ),
                        dto.components.PumpSystem(
                            name="pump_system_v2",
                            user_defined_category={datetime(2022, 1, 1): "PUMP"},
                            regularity=regularity,
                            consumes=dto.types.ConsumptionType.FUEL,
                            operational_settings={
                                datetime(2022, 1, 1, 0, 0): [
                                    dto.components.PumpSystemOperationalSetting(
                                        rates=[
                                            Expression.setup_from_expression(x) for x in [4000000, 5000000, 6000000]
                                        ],
                                        inlet_pressures=[Expression.setup_from_expression("50")] * 3,
                                        outlet_pressures=[Expression.setup_from_expression("250")] * 3,
                                        crossover=[0, 1, 1],
                                        fluid_density=[Expression.setup_from_expression("2")] * 3,
                                    )
                                ]
                            },
                            pumps=[
                                dto.components.PumpComponent(
                                    name="pump1",
                                    user_defined_category={datetime(2022, 1, 1): "PUMP"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
                                    fuel=fuel,
                                ),
                                dto.components.PumpComponent(
                                    name="pump2",
                                    user_defined_category={datetime(2022, 1, 1): "PUMP"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
                                    fuel=fuel,
                                ),
                                dto.components.PumpComponent(
                                    name="pump3",
                                    user_defined_category={datetime(2022, 1, 1): "PUMP"},
                                    regularity=regularity,
                                    consumes=dto.types.ConsumptionType.FUEL,
                                    energy_usage_model={datetime(2022, 1, 1, 0, 0): pump_model_single_speed},
                                    fuel=fuel,
                                ),
                            ],
                        ),
                        dto.FuelConsumer(
                            **{
                                "component_type": ComponentType.COMPRESSOR_SYSTEM,
                                "consumes": dto.types.ConsumptionType.FUEL,
                                "energy_usage_model": {
                                    datetime(2022, 1, 1, 0, 0): {
                                        "compressors": [
                                            {
                                                "compressor_train": {
                                                    "discharge_pressure_values": None,
                                                    "energy_usage_adjustment_constant": 0.0,
                                                    "energy_usage_adjustment_factor": 1.0,
                                                    "energy_usage_type": "FUEL",
                                                    "energy_usage_values": [0.0, 10000.0, 11000.0, 12000.0, 13000.0],
                                                    "power_interpolation_values": [0.0, 1.0, 2.0, 3.0, 4.0],
                                                    "rate_values": [0.0, 1000000.0, 2000000.0, 3000000.0, 4000000.0],
                                                    "suction_pressure_values": None,
                                                    "typ": "COMPRESSOR_SAMPLED",
                                                },
                                                "name": "compressor1",
                                            },
                                            {
                                                "compressor_train": {
                                                    "discharge_pressure_values": None,
                                                    "energy_usage_adjustment_constant": 0.0,
                                                    "energy_usage_adjustment_factor": 1.0,
                                                    "energy_usage_type": "FUEL",
                                                    "energy_usage_values": [0.0, 10000.0, 11000.0, 12000.0, 13000.0],
                                                    "power_interpolation_values": [0.0, 1.0, 2.0, 3.0, 4.0],
                                                    "rate_values": [0.0, 1000000.0, 2000000.0, 3000000.0, 4000000.0],
                                                    "suction_pressure_values": None,
                                                    "typ": "COMPRESSOR_SAMPLED",
                                                },
                                                "name": "compressor2",
                                            },
                                            {
                                                "compressor_train": {
                                                    "discharge_pressure_values": None,
                                                    "energy_usage_adjustment_constant": 0.0,
                                                    "energy_usage_adjustment_factor": 1.0,
                                                    "energy_usage_type": "FUEL",
                                                    "energy_usage_values": [0.0, 10000.0, 11000.0, 12000.0, 13000.0],
                                                    "power_interpolation_values": [0.0, 1.0, 2.0, 3.0, 4.0],
                                                    "rate_values": [0.0, 1000000.0, 2000000.0, 3000000.0, 4000000.0],
                                                    "suction_pressure_values": None,
                                                    "typ": "COMPRESSOR_SAMPLED",
                                                },
                                                "name": "compressor3",
                                            },
                                        ],
                                        "condition": None,
                                        "energy_usage_type": "FUEL",
                                        "operational_settings": [
                                            {
                                                "crossover": [0, 1, 1],
                                                "discharge_pressure": Expression.setup_from_expression(250.0),
                                                "discharge_pressures": None,
                                                "rate_fractions": None,
                                                "rates": [
                                                    Expression.setup_from_expression(x)
                                                    for x in [1000000, 5000000, 6000000]
                                                ],
                                                "suction_pressure": Expression.setup_from_expression(50.0),
                                                "suction_pressures": None,
                                            }
                                        ],
                                        "power_loss_factor": None,
                                        "total_system_rate": None,
                                    }
                                },
                                "fuel": {
                                    datetime(2022, 1, 1, 0, 0): {
                                        "emissions": [
                                            {
                                                "factor": Expression.setup_from_expression(2.2),
                                                "name": "co2",
                                                "quota": None,
                                                "tax": Expression.setup_from_expression(1.51),
                                            }
                                        ],
                                        "name": "fuel_gas",
                                        "price": Expression.setup_from_expression(1.5),
                                        "user_defined_category": "FUEL-GAS",
                                    }
                                },
                                "name": "compressor_system",
                                "regularity": {datetime(2022, 1, 1, 0, 0): Expression.setup_from_expression(1.0)},
                                "user_defined_category": {datetime(2022, 1, 1): "COMPRESSOR"},
                            },
                        ),
                    ],
                    direct_emitters=[],
                )
            ],
        ),
        variables=dto.VariablesMap(time_vector=[datetime(2022, 1, 1, 0, 0), datetime(2026, 1, 1, 0, 0)], variables={}),
    )
