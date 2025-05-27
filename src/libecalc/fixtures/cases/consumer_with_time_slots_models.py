from copy import deepcopy
from datetime import datetime

import pytest

from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.common.time_utils import Period
from libecalc.common.variables import VariablesMap
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.compressor.dto import (
    CompressorConsumerFunction,
    CompressorStage,
    SingleSpeedCompressorTrain,
)
from libecalc.domain.process.dto import (
    DirectConsumerFunction,
    TabulatedConsumerFunction,
    TabulatedData,
    Variables,
)
from libecalc.domain.process.dto.consumer_system import (
    CompressorSystemCompressor,
    CompressorSystemConsumerFunction,
    CompressorSystemOperationalSetting,
)
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.fixtures.case_types import DTOCase
from libecalc.presentation.yaml.yaml_entities import MemoryResource


def direct_consumer(power: float) -> DirectConsumerFunction:
    return DirectConsumerFunction(
        load=Expression.setup_from_expression(value=power),
        energy_usage_type=EnergyUsageType.POWER,
    )


def generator_set_sampled_300mw() -> GeneratorSetModel:
    resource = MemoryResource(
        headers=["POWER", "FUEL"],
        data=[[0, 1, 300], [0, 1, 300]],
    )
    return GeneratorSetModel(
        name="generator_set_sampled_300mw",
        resource=resource,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


def tabulated_energy_usage_model() -> TabulatedConsumerFunction:
    return TabulatedConsumerFunction(
        model=TabulatedData(
            headers=["RATE", "FUEL"],
            data=[[0, 1, 2, 10000], [0, 2, 4, 5]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        ),
        variables=[Variables(name="RATE", expression=Expression.setup_from_expression(value="RATE"))],
        energy_usage_type=EnergyUsageType.FUEL,
    )


def tabulated_fuel_consumer_with_time_slots(fuel_gas, time_vector=None, variables=None) -> FuelConsumer:
    if time_vector is None:
        time_vector = [datetime(1900, 1, 1), datetime.max]
    if variables is None:
        variables = {}

    expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
    return FuelConsumer(
        path_id=PathID("fuel_consumer_with_time_slots"),
        component_type=ComponentType.GENERIC,
        fuel=fuel_gas,
        regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
        energy_usage_model={
            Period(datetime(1900, 1, 1), datetime(2019, 1, 1)): tabulated_energy_usage_model(),
            Period(datetime(2019, 1, 1)): tabulated_energy_usage_model(),
        },
        user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
        expression_evaluator=VariablesMap(time_vector=time_vector, variables=variables),
    )


def single_speed_compressor_chart() -> SingleSpeedChartDTO:
    """A simple single speed compressor chart."""
    return SingleSpeedChartDTO(
        rate_actual_m3_hour=[x * 1000 for x in range(1, 11)],  # 1000 -> 10 000
        polytropic_head_joule_per_kg=[100000 - (x * 10000) for x in range(10)],  # 100 000 -> 10 000
        efficiency_fraction=[round(1 - (x / 10), 1) for x in range(10)],  # 1 -> 0.1
        speed_rpm=1,
    )


@pytest.fixture
def single_speed_compressor_train(medium_fluid_dto) -> SingleSpeedCompressorTrain:
    return SingleSpeedCompressorTrain(
        fluid_model=medium_fluid_dto,
        stages=[
            CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=single_speed_compressor_chart(),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
            CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=single_speed_compressor_chart(),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
        ],
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        maximum_discharge_pressure=350.0,
        energy_usage_adjustment_constant=1.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def simple_compressor_model(single_speed_compressor_train) -> CompressorConsumerFunction:
    return CompressorConsumerFunction(
        energy_usage_type=EnergyUsageType.POWER,
        rate_standard_m3_day=Expression.setup_from_expression(value="RATE"),
        suction_pressure=Expression.setup_from_expression(value=20),
        discharge_pressure=Expression.setup_from_expression(value=200),
        model=single_speed_compressor_train,
    )


@pytest.fixture
def time_slot_electricity_consumer_with_changing_model_type(simple_compressor_model):
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}
        expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
        return ElectricityConsumer(
            path_id=PathID("el-consumer1"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
            regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
            energy_usage_model={
                # Starting with a direct consumer because we don't know everything in the past
                Period(datetime(2017, 1, 1), datetime(2018, 1, 1)): direct_consumer(power=5),
                # Then we know some more. So we model it as a simplified model
                Period(datetime(2018, 1, 1), datetime(2024, 1, 1)): simple_compressor_model,
                # Finally we decommission the equipment by setting direct consumer to zero load.
                Period(datetime(2024, 1, 1)): direct_consumer(power=0),
            },
            expression_evaluator=expression_evaluator,
        )

    return _create


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type():
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}

        expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
        return ElectricityConsumer(
            path_id=PathID("el-consumer2"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
            regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
            energy_usage_model={
                Period(datetime(2017, 1, 1), datetime(2019, 1, 1)): direct_consumer(power=5),
                Period(datetime(2019, 1, 1), datetime(2024, 1, 1)): direct_consumer(power=10),
                Period(datetime(2024, 1, 1)): direct_consumer(power=0),
            },
            expression_evaluator=expression_evaluator,
        )

    return _create


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type2():
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        """Same consumer as 'time_slot_electricity_consumer_with_same_model_type', different name,
        used in the second generator set.
        """
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}
        expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
        return ElectricityConsumer(
            path_id=PathID("el-consumer4"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
            regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
            energy_usage_model={
                Period(datetime(2017, 1, 1), datetime(2019, 1, 1)): direct_consumer(power=5),
                Period(datetime(2019, 1, 1), datetime(2024, 1, 1)): direct_consumer(power=10),
                Period(datetime(2024, 1, 1)): direct_consumer(power=0),
            },
            expression_evaluator=expression_evaluator,
        )

    return _create


@pytest.fixture
def time_slot_electricity_consumer_with_same_model_type3(simple_compressor_model):
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}
        expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
        return ElectricityConsumer(
            path_id=PathID("el-consumer-simple-compressor-model-with-timeslots"),
            component_type=ComponentType.COMPRESSOR,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
            regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
            energy_usage_model={
                Period(datetime(2017, 1, 1), datetime(2019, 1, 1)): simple_compressor_model,
                Period(datetime(2019, 1, 1), datetime(2024, 1, 1)): simple_compressor_model,
                Period(datetime(2024, 1, 1)): simple_compressor_model,
            },
            expression_evaluator=expression_evaluator,
        )

    return _create


@pytest.fixture
def time_slot_electricity_consumer_too_late_startup():
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}
        return ElectricityConsumer(
            path_id=PathID("el-consumer3"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR},
            energy_usage_model={Period(datetime(2050, 1, 1)): direct_consumer(power=5)},
            regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression(value=1)},
            expression_evaluator=VariablesMap(time_vector=time_vector, variables=variables),
        )

    return _create


@pytest.fixture
def time_slots_simplified_compressor_system(
    fuel_gas,
    single_speed_compressor_train,
):
    def _create(time_vector=None, variables=None) -> ElectricityConsumer:
        """Here we model a compressor system that changes over time. New part is suffixed "_upgrade"."""
        if time_vector is None:
            time_vector = [datetime(1900, 1, 1), datetime.max]
        if variables is None:
            variables = {}
        energy_usage_model = CompressorSystemConsumerFunction(
            energy_usage_type=EnergyUsageType.POWER,
            compressors=[
                CompressorSystemCompressor(
                    name="train1",
                    compressor_train=single_speed_compressor_train,
                ),
                CompressorSystemCompressor(
                    name="train2",
                    compressor_train=single_speed_compressor_train,
                ),
            ],
            operational_settings=[
                CompressorSystemOperationalSetting(
                    rate_fractions=[
                        Expression.setup_from_expression(value=1),
                        Expression.setup_from_expression(value=0),
                    ],
                    suction_pressure=Expression.setup_from_expression(value=41),
                    discharge_pressure=Expression.setup_from_expression(value=200),
                ),
                CompressorSystemOperationalSetting(
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
        expression_evaluator = VariablesMap(time_vector=time_vector, variables=variables)
        return ElectricityConsumer(
            path_id=PathID("simplified_compressor_system"),
            component_type=ComponentType.COMPRESSOR_SYSTEM,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.COMPRESSOR},
            regularity=Regularity.create(expression_evaluator=expression_evaluator, expression_input=1),
            energy_usage_model={
                Period(datetime(1900, 1, 1), datetime(2019, 1, 1)): energy_usage_model,
                Period(datetime(2019, 1, 1)): energy_usage_model_upgrade,
            },
            expression_evaluator=expression_evaluator,
        )

    return _create


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
    time_vector = [datetime(year, 1, 1) for year in range(start_year, start_year + number_of_years + 1)]
    variables = {"RATE": [5000] * number_of_years}
    variables_map = VariablesMap(time_vector=time_vector, variables=variables)
    regularity = Regularity.create(expression_evaluator=variables_map, expression_input=1)
    hydrocarbon_export = HydrocarbonExport.create(
        expression_evaluator=variables_map, expression_input="RATE", regularity=regularity
    )

    return DTOCase(
        ecalc_model=Asset(
            path_id=PathID("time_slots_model"),
            installations=[
                Installation(
                    user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                    path_id=PathID("some_installation"),
                    regularity=regularity,
                    hydrocarbon_export=hydrocarbon_export,
                    fuel_consumers=[
                        GeneratorSetEnergyComponent(
                            path_id=PathID("some_genset"),
                            user_defined_category={
                                Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                Period(datetime(1900, 1, 1)): generator_set_sampled_300mw(),
                            },
                            fuel=fuel_gas,
                            regularity=regularity,
                            consumers=[
                                time_slot_electricity_consumer_with_same_model_type(time_vector, variables),
                                time_slot_electricity_consumer_with_same_model_type3(time_vector, variables),
                                time_slot_electricity_consumer_too_late_startup(time_vector, variables),
                                time_slots_simplified_compressor_system(time_vector, variables),
                            ],
                            expression_evaluator=variables_map,
                        ),
                        GeneratorSetEnergyComponent(
                            path_id=PathID("some_genset_startup_after_consumer"),
                            user_defined_category={
                                Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
                            },
                            generator_set_model={
                                # 2 years after the consumers start.
                                Period(datetime(2019, 1, 1)): generator_set_sampled_300mw(),
                            },
                            fuel=fuel_gas,
                            regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression(value=1)},
                            consumers=[time_slot_electricity_consumer_with_same_model_type2(time_vector, variables)],
                            expression_evaluator=variables_map,
                        ),
                        tabulated_fuel_consumer_with_time_slots(fuel_gas, time_vector=time_vector, variables=variables),
                    ],
                    venting_emitters=[],
                    expression_evaluator=variables_map,
                )
            ],
        ),
        variables=variables_map,
    )
