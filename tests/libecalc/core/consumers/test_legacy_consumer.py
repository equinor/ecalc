from datetime import datetime
from io import StringIO
from typing import Union
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import VariablesMap
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.core.result import EcalcModelResult
from libecalc.dto.types import (
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
    FuelTypeUserDefinedCategoryType,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModelType
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlDefaultTimeSeriesCollection

from libecalc.testing.yaml_builder import (
    YamlElectricityConsumerBuilder,
    YamlInstallationBuilder,
    YamlAssetBuilder,
    YamlGeneratorSetBuilder,
    YamlElectricity2fuelBuilder,
    YamlFuelTypeBuilder,
    YamlFuelConsumerBuilder,
    YamlTabularBuilder,
    YamlTabulatedVariableBuilder,
    YamlTimeSeriesBuilder,
)


class ConsumerTestHelper:
    def __init__(self):
        # Constants
        self.rate_name = "RATE"
        self.fuel_rate_name = "FUEL_RATE"
        self.power_name = "POWER"
        self.fuel_name = "FUEL"
        self.date_name = "DATE"
        self.file_name = "SIM1"

        # Rates etc.
        self.fuel_rates = [1, 1, 1, 1, 0, 0]

        # Dates and periods
        self.d1900 = datetime(1900, 1, 1)
        self.d2020 = datetime(2020, 1, 1)
        self.d2021 = datetime(2021, 1, 1)
        self.d2022 = datetime(2022, 1, 1)
        self.d2023 = datetime(2023, 1, 1)
        self.d2026 = datetime(2026, 1, 1)

        self.p1900 = Period(self.d1900)

        self.time_vector = pd.date_range(self.d2020, self.d2026, freq="YS").to_pydatetime().tolist()
        self.regularity = TemporalModel({self.p1900: Expression.setup_from_expression(1)})

    def build_consumer(
        self, consumer_name: str, component_type: ComponentType, consumes: ConsumptionType, energy_usage_model: dict
    ):
        return Consumer(
            id=consumer_name,
            name=consumer_name,
            component_type=component_type,
            regularity=self.regularity,
            consumes=consumes,
            energy_usage_model=TemporalModel(
                {
                    start_time: EnergyModelMapper.from_dto_to_domain(model)
                    for start_time, model in energy_usage_model.items()
                }
            ),
        )

    def setup_test_environment(self, request):
        variables = self.variables_map()
        asset = self.get_default_asset(request)
        resources = {
            self.generator_fuel_energy_function().name: self.generator_el2fuel_2mw_resource,
        }
        yaml_model = self.get_yaml_model(request, asset, resources, Frequency.NONE)
        return variables, yaml_model

    def variables_map(self, time_vector=None, variables: dict = None):
        variables = variables if variables else {}
        time_vector = time_vector if time_vector else self.time_vector
        return VariablesMap(time_vector=time_vector, variables=variables)

    def memory_resource_factory(self, data: list[list[Union[float, int, str]]], headers: list[str]) -> MemoryResource:
        return MemoryResource(
            data=data,
            headers=headers,
        )

    def get_yaml_model(
        self,
        request,
        asset: Union[YamlAsset],
        resources: dict[str, MemoryResource],
        frequency: Frequency = Frequency.NONE,
    ) -> YamlModel:
        yaml_model_factory = request.getfixturevalue("yaml_model_factory")
        asset_dict = asset.model_dump(
            serialize_as_any=True,
            mode="json",
            exclude_unset=True,
            by_alias=True,
        )

        yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
        stream = ResourceStream(name="", stream=StringIO(yaml_string))
        yaml_model = yaml_model_factory(resource_stream=stream, resources=resources, frequency=frequency)

        yaml_model.models = []
        yaml_model.facility_inputs = []
        yaml_model.time_series = []

        return yaml_model

    @property
    def generator_el2fuel_2mw_resource(self):
        return self.memory_resource_factory(
            data=[[0, 0.5, 1, 2], [0, 0.6, 1, 2]],
            headers=[
                self.power_name,
                self.fuel_name,
            ],
        )

    @property
    def tabulated_fuel_resource(self):
        return self.memory_resource_factory(
            data=[[0, 1, 2], [0, 2, 4]],
            headers=[
                self.rate_name,
                self.fuel_name,
            ],
        )

    @property
    def fuel_time_series_resource(self):
        time_str = [str(time) for time in self.time_vector]
        return self.memory_resource_factory(
            data=[time_str[:-1], self.fuel_rates],
            headers=[
                self.date_name,
                self.fuel_rate_name,
            ],
        )

    @property
    def fuel_rate_time_series(self):
        return (YamlTimeSeriesBuilder().with_name(self.file_name).with_file(self.file_name)).validate()

    @property
    def fuel(self):
        return (
            YamlFuelTypeBuilder()
            .with_name("fuel_gas")
            .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
            .with_emission_names_and_factors(names=["co2"], factors=[1])
        ).validate()

    @property
    def tabulated_variable(self):
        return (
            YamlTabulatedVariableBuilder()
            .with_name(self.rate_name)
            .with_expression(self.file_name + ";" + self.fuel_rate_name)
        ).validate()

    def generator_fuel_energy_function(self, name_extension="2mw"):
        return (
            YamlElectricity2fuelBuilder()
            .with_name("generator_fuel_energy_function_" + name_extension)
            .with_file("generator_fuel_energy_function_" + name_extension)
        ).validate()

    def tabular_fuel_energy_function(self, name_extension="1"):
        return (
            YamlTabularBuilder()
            .with_name("tabular_fuel_energy_function_" + name_extension)
            .with_file("tabular_fuel_energy_function_" + name_extension)
        ).validate()

    def genset_2mw(self, request, consumers: list[YamlElectricityConsumer] = None):
        if not consumers:
            consumers = [self.direct_electricity_consumer(request)]

        return (
            YamlGeneratorSetBuilder()
            .with_name("genset")
            .with_category({self.d1900: "TURBINE-GENERATOR"})
            .with_fuel({self.d1900: self.fuel.name})
            .with_electricity2fuel({self.d1900: self.generator_fuel_energy_function().name})
            .with_consumers(consumers)
        ).validate()

    def direct_electricity_consumer(self, request):
        energy_usage_model_direct_load_factory = request.getfixturevalue("energy_usage_model_direct_load_factory")
        return (
            YamlElectricityConsumerBuilder()
            .with_name("direct_consumer")
            .with_category({self.d1900: ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD})
            .with_energy_usage_model(
                {
                    self.d2020: energy_usage_model_direct_load_factory(1),
                    self.d2021: energy_usage_model_direct_load_factory(2),
                    self.d2022: energy_usage_model_direct_load_factory(10),
                    self.d2023: energy_usage_model_direct_load_factory(0),
                }
            )
        ).validate()

    def fuel_consumer(self, request, fuel: YamlFuelType = None, category: ConsumerUserDefinedCategoryType = None):
        energy_usage_model_tabular = request.getfixturevalue("energy_usage_model_tabular_factory")(
            variables=[self.tabulated_variable], energy_function=self.tabular_fuel_energy_function().name
        )

        consumer = (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_energy_usage_model({self.d1900: energy_usage_model_tabular})
        )

        if fuel:
            consumer.fuel = fuel.name
        else:
            consumer.fuel = self.fuel.name

        if category:
            consumer.category = category
        else:
            consumer.category = ConsumerUserDefinedCategoryType.MISCELLANEOUS

        return consumer.validate()

    def installation(self, generator_set: list[YamlGeneratorSet] = None, fuel_consumers: list[YamlFuelConsumer] = None):
        installation = (
            YamlInstallationBuilder()
            .with_name("DefaultInstallation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_regularity(1)
        )

        if generator_set:
            installation.generator_sets = generator_set
        if fuel_consumers:
            installation.fuel_consumers = fuel_consumers

        return installation.validate()

    def asset(
        self,
        installations: list[YamlInstallation],
        facility_inputs: list[YamlFacilityModelType] = None,
        fuel_types: list[YamlFuelType] = None,
        time_series: list[YamlDefaultTimeSeriesCollection] = None,
    ):
        asset = YamlAssetBuilder().with_installations(installations).with_start(self.d2020).with_end(self.d2026)

        if facility_inputs:
            asset.facility_inputs = facility_inputs
        if time_series:
            asset.time_series = time_series
        if fuel_types:
            asset.fuel_types = fuel_types
        else:
            asset.fuel_types = [self.fuel]

        return asset.validate()

    def get_default_asset(self, request):
        generator_set = self.genset_2mw(request)
        installations = self.installation([generator_set])
        facility_inputs = self.generator_fuel_energy_function()
        return self.asset(installations=[installations], facility_inputs=[facility_inputs])


@pytest.fixture
def consumer_test_helper():
    return ConsumerTestHelper()


class TestConsumer:
    def test_evaluate_consumer_time_function(self, consumer_test_helper, request):
        """Testing using a direct el consumer for simplicity."""
        variables, yaml_model = consumer_test_helper.setup_test_environment(request)
        direct_el_consumer = yaml_model.get_graph().get_node(
            consumer_test_helper.direct_electricity_consumer(request).name
        )

        consumer = consumer_test_helper.build_consumer(
            consumer_name=direct_el_consumer.name,
            component_type=ComponentType.GENERIC,
            consumes=ConsumptionType.ELECTRICITY,
            energy_usage_model=direct_el_consumer.energy_usage_model,
        )

        results = consumer.evaluate_consumer_temporal_model(
            expression_evaluator=variables, regularity=np.ones_like(variables.periods).tolist()
        )
        results = consumer.aggregate_consumer_function_results(results)
        assert results.energy_usage.tolist() == [1, 2, 10, 0, 0, 0]
        assert results.is_valid.tolist() == [1, 1, 1, 1, 1, 1]
        assert results.periods == variables.periods

    def test_fuel_consumer(self, consumer_test_helper, request):
        """Simple test to assert that the FuelConsumer actually runs as expected."""

        yaml_fuel_consumer = consumer_test_helper.fuel_consumer(request)

        installation = (
            YamlInstallationBuilder().with_name("installation").with_fuel_consumers([yaml_fuel_consumer])
        ).validate()

        asset = consumer_test_helper.asset(
            installations=[installation],
            facility_inputs=[consumer_test_helper.tabular_fuel_energy_function()],
            time_series=[consumer_test_helper.fuel_rate_time_series],
        )

        resources = {
            consumer_test_helper.tabular_fuel_energy_function().name: consumer_test_helper.tabulated_fuel_resource,
            consumer_test_helper.fuel_rate_time_series.name: consumer_test_helper.fuel_time_series_resource,
        }

        yaml_model = consumer_test_helper.get_yaml_model(request, asset, resources, frequency=Frequency.NONE)
        fuel_consumer_yaml = yaml_model.get_graph().get_node(consumer_test_helper.fuel_consumer(request).name)

        fuel_consumer = consumer_test_helper.build_consumer(
            fuel_consumer_yaml.name,
            fuel_consumer_yaml.component_type,
            fuel_consumer_yaml.consumes,
            fuel_consumer_yaml.energy_usage_model,
        )

        variables_input = {
            consumer_test_helper.file_name + ";" + consumer_test_helper.fuel_rate_name: consumer_test_helper.fuel_rates,
        }
        variables = consumer_test_helper.variables_map(variables=variables_input)

        result = fuel_consumer.evaluate(
            expression_evaluator=variables,
        )
        consumer_result = result.component_result

        assert consumer_result.energy_usage == TimeSeriesRate(
            periods=variables.periods,
            values=[2, 2, 2, 2, 0, 0],
            regularity=[1] * 6,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
        )
        assert consumer_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[True] * 6,
            unit=Unit.NONE,
        )

        assert consumer_result.periods == variables.periods

    def test_electricity_consumer(self, consumer_test_helper, request):
        """Simple test to assert that the FuelConsumer actually runs as expected."""
        variables, yaml_model = consumer_test_helper.setup_test_environment(request)
        direct_el_consumer = yaml_model.get_graph().get_node(
            consumer_test_helper.direct_electricity_consumer(request).name
        )

        electricity_consumer = consumer_test_helper.build_consumer(
            direct_el_consumer.id,
            direct_el_consumer.component_type,
            direct_el_consumer.consumes,
            direct_el_consumer.energy_usage_model,
        )

        result = electricity_consumer.evaluate(
            expression_evaluator=variables,
        )

        assert isinstance(result, EcalcModelResult)
        consumer_result = result.component_result
        assert consumer_result.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[1, 2, 10, 0, 0, 0],
            unit=Unit.MEGA_WATT,
        )
        assert consumer_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[True] * 6,
            unit=Unit.NONE,
        )
        assert consumer_result.periods == variables.periods

    def test_electricity_consumer_mismatch_time_slots(self, consumer_test_helper, request):
        """The direct_el_consumer starts after the ElectricityConsumer is finished."""
        time_vector_mismatch_timeslots = (
            pd.date_range(datetime(2000, 1, 1), datetime(2005, 1, 1), freq="YS").to_pydatetime().tolist()
        )
        variables = consumer_test_helper.variables_map(time_vector=time_vector_mismatch_timeslots)

        asset = consumer_test_helper.get_default_asset(request)

        resources = {
            consumer_test_helper.generator_fuel_energy_function().name: consumer_test_helper.generator_el2fuel_2mw_resource,
        }

        yaml_model = consumer_test_helper.get_yaml_model(request, asset, resources, Frequency.NONE)

        direct_el_consumer = yaml_model.get_graph().get_node(
            consumer_test_helper.direct_electricity_consumer(request).name
        )

        electricity_consumer = consumer_test_helper.build_consumer(
            direct_el_consumer.id,
            direct_el_consumer.component_type,
            direct_el_consumer.consumes,
            direct_el_consumer.energy_usage_model,
        )

        result = electricity_consumer.evaluate(
            expression_evaluator=variables,
        )
        consumer_result = result.component_result

        # The consumer itself should however return a proper result object matching the input time_vector.
        assert consumer_result.periods == variables.periods
        assert consumer_result.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[0] * len(variables.periods),
            unit=Unit.MEGA_WATT,
        )
        assert consumer_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[True] * len(variables.periods),
            unit=Unit.NONE,
        )

    def test_electricity_consumer_nan_values(self, consumer_test_helper, request):
        """1. When the resulting power starts with NaN, these values will be filled with zeros.
        2. When a valid power result is followed by NaN-values,
            then these are forward filled when extrapcorrection is True.
            If not, they are filled with zeros and extrapolation is False.
        3. Only valid power from the consumer function results are reported as valid results.

        :param direct_el_consumer:
        :return:
        """
        variables, yaml_model = consumer_test_helper.setup_test_environment(request)
        direct_el_consumer = yaml_model.get_graph().get_node(
            consumer_test_helper.direct_electricity_consumer(request).name
        )

        power = np.array([np.nan, np.nan, 1, np.nan, np.nan, np.nan])
        electricity_consumer = consumer_test_helper.build_consumer(
            direct_el_consumer.id,
            direct_el_consumer.component_type,
            direct_el_consumer.consumes,
            direct_el_consumer.energy_usage_model,
        )

        consumer_function_result = ConsumerFunctionResult(
            power=power,
            energy_usage=power,
            periods=variables.periods,
            is_valid=np.asarray([False, False, True, False, False, False]),
        )

        electricity_consumer.evaluate_consumer_temporal_model = Mock(return_value=[consumer_function_result])

        result = electricity_consumer.evaluate(
            expression_evaluator=variables,
        )
        consumer_result = result.component_result

        assert consumer_result.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[0, 0, 1, 1, 1, 1],
            unit=Unit.MEGA_WATT,
        )
        assert consumer_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[False, False, True, False, False, False],
            unit=Unit.NONE,
        )
