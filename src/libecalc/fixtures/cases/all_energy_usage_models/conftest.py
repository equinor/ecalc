from datetime import datetime
from typing import Dict

import pytest

from libecalc import dto
from libecalc.common.units import Unit
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.fluid_mapper import MEDIUM_MW_19P4


@pytest.fixture
def all_energy_usage_models_variables():
    variables = {
        **{
            "SIM1;OIL_PROD": [5016.0, 4092.0, 3483.0, 3051.0],
            "SIM1;WATER_PROD": [23410.0, 24920.0, 25807.0, 23196.0],
            "SIM1;GAS_PROD": [6070485.0, 4744704.0, 5334699.0, 5676338.0],
            "SIM1;WATER_INJ": [31977.0, 28750.0, 29128.0, 25270.0],
            "SIM1;GAS_LIFT": [60704.85, 60704.85, 60704.85, 60704.85],
            "SIM1;REGULARITY": [1.0, 1.0, 1.0, 0.0],
            "SIM1;POWERLOSS_CONSTANT": [0.0, 0.0, 0.024, 0.04],
            "FLARE;FLARE_RATE": [10000.0, 10000.0, 14000.0, 14000.0],
            "FLARE;METHANE_RATE": [3.0, 3.0, 6.0, 6.0],
            "$var.salt_water_injection": [8567.0, 3830.0, 3321.0, 2074.0],
        },
    }
    time_vector = [
        datetime(2017, 1, 1, 0, 0),
        datetime(2018, 1, 1, 0, 0),
        datetime(2019, 1, 1, 0, 0),
        datetime(2020, 1, 1, 0, 0),
    ]
    return dto.VariablesMap(time_vector=time_vector, variables=variables)


@pytest.fixture
def single_speed_pump() -> dto.PumpModel:
    chart = dto.SingleSpeedChart(
        rate_actual_m3_hour=[200.0, 500.0, 1000.0, 1300.0, 1500.0],
        polytropic_head_joule_per_kg=[
            Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
            for x in [3000.0, 2500.0, 2400.0, 2000.0, 1900.0]
        ],
        efficiency_fraction=[0.4, 0.5, 0.6, 0.7, 0.8],
        speed_rpm=1,
    )
    return dto.PumpModel(
        chart=chart,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        head_margin=0.0,
    )


@pytest.fixture
def variable_speed_pump() -> dto.PumpModel:
    return dto.PumpModel(
        chart=dto.VariableSpeedChart(
            curves=[
                dto.ChartCurve(
                    rate_actual_m3_hour=[250, 500, 700, 800, 850, 900],
                    polytropic_head_joule_per_kg=[
                        Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                        for x in [
                            1050.0,
                            1000.0,
                            900.0,
                            880.0,
                            860.0,
                            840.0,
                        ]
                    ],  # meter liquid column, may need conv.
                    efficiency_fraction=[0.5, 0.65, 0.7, 0.75, 0.75, 0.75],
                    speed_rpm=2650,
                ),
                dto.ChartCurve(
                    rate_actual_m3_hour=[300.0, 600.0, 700.0, 800.0, 850.0, 900.0, 1000.0, 1300.0],
                    polytropic_head_joule_per_kg=[
                        Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                        for x in [
                            1800.0,
                            1700.0,
                            1650.0,
                            1600.0,
                            1600.0,
                            1550.0,
                            1500.0,
                            1300.0,
                        ]
                    ],
                    efficiency_fraction=[0.5, 0.65, 0.7, 0.75, 0.75, 0.75, 0.75, 0.75],
                    speed_rpm=3450,
                ),
            ]
        ),
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=0.8,
        head_margin=0.0,
    )


@pytest.fixture
def simplified_variable_speed_compressor_train_with_gerg_fluid2(predefined_variable_speed_compressor_chart_dto):
    return dto.CompressorTrainSimplifiedWithKnownStages(
        fluid_model=dto.FluidModel(
            eos_model=dto.types.EoSModel.GERG_SRK, composition=dto.FluidComposition.parse_obj(MEDIUM_MW_19P4)
        ),
        stages=[
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=predefined_variable_speed_compressor_chart_dto,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
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
    )


@pytest.fixture
def user_defined_single_speed_compressor_chart_dto() -> dto.SingleSpeedChart:
    return dto.SingleSpeedChart(
        rate_actual_m3_hour=[1735, 1882, 2027, 2182, 2322, 2467, 2615, 2762, 2907, 3054, 3201],
        polytropic_head_joule_per_kg=[95942, 92999, 89663, 86426, 81325, 76126, 70142, 63569, 56604, 49639, 42477],
        efficiency_fraction=[
            0.7121,
            0.7214,
            0.7281,
            0.7286,
            0.7194,
            0.7108,
            0.7001,
            0.6744,
            0.6364,
            0.5859,
            0.5185,
        ],
        speed_rpm=1,
    )


@pytest.fixture
def compressor_sampled_1d():
    return dto.CompressorSampled(
        energy_usage_type=dto.types.EnergyUsageType.FUEL,
        energy_usage_values=[0, 10000, 11000, 12000, 13000],
        power_interpolation_values=[0.0, 1.0, 2.0, 3.0, 4.0],
        rate_values=[0, 1000000, 2000000, 3000000, 4000000],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def compressor_with_turbine(turbine_dto, simplified_variable_speed_compressor_train_known_stages):
    return dto.CompressorWithTurbine(
        compressor_train=simplified_variable_speed_compressor_train_known_stages,
        turbine=turbine_dto,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def turbine_dto() -> dto.Turbine:
    return dto.Turbine(
        lower_heating_value=38.0,
        turbine_loads=[0.0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
        turbine_efficiency_fractions=[0.0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture()
def compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2(
    turbine_dto,
    predefined_variable_speed_compressor_chart_dto,
) -> dto.CompressorWithTurbine:
    dto_stage = dto.CompressorStage(
        compressor_chart=predefined_variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=0,
        control_margin=0,
    )
    return dto.CompressorWithTurbine(
        turbine=turbine_dto,
        compressor_train=dto.VariableSpeedCompressorTrain(
            fluid_model=dto.FluidModel(
                composition=dto.FluidComposition(
                    water=0.0,
                    nitrogen=0.74373,
                    CO2=2.415619,
                    methane=85.60145,
                    ethane=6.707826,
                    propane=2.611471,
                    i_butane=0.45077,
                    n_butane=0.691702,
                    i_pentane=0.210714,
                    n_pentane=0.197937,
                    n_hexane=0.368786,
                ),
                eos_model=dto.types.EoSModel.SRK,
            ),
            stages=[dto_stage, dto_stage],
            energy_usage_adjustment_constant=1.0,
            energy_usage_adjustment_factor=1.0,
            pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        ),
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def regularity() -> Dict[datetime, Expression]:
    return {datetime(1900, 1, 1): Expression.setup_from_expression(value="SIM1;REGULARITY")}


@pytest.fixture
def simplified_variable_speed_compressor_train_known_stages(
    predefined_variable_speed_compressor_chart_dto, medium_fluid_dto
):
    return dto.CompressorTrainSimplifiedWithKnownStages(
        fluid_model=medium_fluid_dto,
        stages=[
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=predefined_variable_speed_compressor_chart_dto,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=predefined_variable_speed_compressor_chart_dto,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
        ],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def methane_values():
    return [0.005, 1.5, 3, 4]
