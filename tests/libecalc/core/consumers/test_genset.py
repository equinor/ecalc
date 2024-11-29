from datetime import datetime
from io import StringIO
from typing import Union

import numpy as np
import pandas as pd
import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import VariablesMap
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result.results import GenericComponentResult
from libecalc.dto.types import (
    FuelTypeUserDefinedCategoryType,
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModelType
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.testing.yaml_builder import (
    YamlGeneratorSetBuilder,
    YamlFuelTypeBuilder,
    YamlElectricityConsumerBuilder,
    YamlElectricity2fuelBuilder,
    YamlInstallationBuilder,
    YamlAssetBuilder,
)


class GensetTestHelper:
    def __init__(self):
        self.d1900 = datetime(1900, 1, 1)
        self.d2020 = datetime(2020, 1, 1)
        self.d2021 = datetime(2021, 1, 1)
        self.d2022 = datetime(2022, 1, 1)
        self.d2023 = datetime(2023, 1, 1)
        self.d2026 = datetime(2026, 1, 1)

        self.p1900 = Period(self.d1900)

        self.time_vector = pd.date_range(self.d2020, self.d2026, freq="YS").to_pydatetime().tolist()

    def memory_resource_factory(self, data: list[list[Union[float, int, str]]], headers: list[str]) -> MemoryResource:
        return MemoryResource(
            data=data,
            headers=headers,
        )

    def get_yaml_model(
        self,
        request,
        asset: YamlAsset,
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

        return yaml_model_factory(resource_stream=stream, resources=resources, frequency=frequency)

    def get_results(self, yaml_model: YamlModel, variables: VariablesMap, component_name: str):
        class LocalResult:
            def __init__(self):
                self.component_result = None
                self.generator_set_result = None
                self.consumer_results = None
                self.energy_calculator = None
                self.components = None

        local_result = LocalResult()
        local_result.energy_calculator = EnergyCalculator(energy_model=yaml_model, expression_evaluator=variables)
        local_result.consumer_results = local_result.energy_calculator.evaluate_energy_usage()

        graph = yaml_model.get_graph()
        local_result.generator_set_result = local_result.consumer_results[component_name].component_result
        local_result.components = [
            local_result.consumer_results[successor].component_result
            for successor in graph.get_successors(component_name)
        ]
        return local_result

    def generator_el2fuel_2mw_resource(self):
        return self.memory_resource_factory(
            data=[[0, 0.5, 1, 2], [0, 0.6, 1, 2]],
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    def generator_el2fuel_1000mw_resource(self):
        return self.memory_resource_factory(
            data=[[0, 0.1, 1, 1000], [0, 0.1, 1, 1000]],
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    def generator_fuel_energy_function(self, name_extension="2mw"):
        return (
            YamlElectricity2fuelBuilder()
            .with_name("generator_fuel_energy_function_" + name_extension)
            .with_file("generator_fuel_energy_function_" + name_extension)
        ).validate()

    def fuel(self):
        return (
            YamlFuelTypeBuilder()
            .with_name("fuel_gas")
            .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
            .with_emission_names_and_factors(names=["co2"], factors=[1])
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

    def genset_2mw(self, request):
        return (
            YamlGeneratorSetBuilder()
            .with_name("genset")
            .with_category({self.d1900: "TURBINE-GENERATOR"})
            .with_fuel({self.d1900: self.fuel().name})
            .with_electricity2fuel({self.d1900: self.generator_fuel_energy_function().name})
            .with_consumers([self.direct_electricity_consumer(request)])
        ).validate()

    def genset_1000mw_late_start(self, request):
        return (
            YamlGeneratorSetBuilder()
            .with_name("genset")
            .with_category({self.d1900: "TURBINE-GENERATOR"})
            .with_fuel({self.d1900: self.fuel().name})
            .with_electricity2fuel({self.d2022: self.generator_fuel_energy_function("1000mw").name})
            .with_consumers([self.direct_electricity_consumer(request)])
        ).validate()

    def installation(self, generator_set: YamlGeneratorSet, request):
        return (
            YamlInstallationBuilder()
            .with_name("DefaultInstallation")
            .with_generator_sets([generator_set])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_regularity(1)
        ).validate()

    def asset(
        self,
        installation: YamlInstallation,
        facility_inputs: list[YamlFacilityModelType] = None,
        fuel_types: list[YamlFuelType] = None,
    ):
        asset = YamlAssetBuilder().with_installations([installation]).with_start(self.d2020).with_end(self.d2026)

        if facility_inputs:
            asset.facility_inputs = facility_inputs
        if fuel_types:
            asset.fuel_types = fuel_types
        else:
            asset.fuel_types = [self.fuel()]

        return asset.validate()


@pytest.fixture
def genset_test_helper():
    return GensetTestHelper()


class TestGenset:
    def test_genset_out_of_capacity2(self, genset_test_helper, request):
        """Testing a genset at capacity, at zero and above capacity.

        Note that extrapcorrection does not have any effect on the Genset itself - but may have an effect on the elconsumer.
        """
        time_vector = genset_test_helper.time_vector
        variables = VariablesMap(time_vector=time_vector)

        generator = genset_test_helper.genset_2mw(request)
        installation = genset_test_helper.installation(generator, request)
        asset = genset_test_helper.asset(
            installation=installation,
            facility_inputs=[genset_test_helper.generator_fuel_energy_function()],
        )
        resources = {
            genset_test_helper.generator_fuel_energy_function().name: genset_test_helper.generator_el2fuel_2mw_resource(),
        }
        yaml_model = genset_test_helper.get_yaml_model(request, asset, resources)

        results = genset_test_helper.get_results(yaml_model, variables, generator.name)

        # Note that this discrepancy between power rate and fuel rate will normally not happen, since the el-consumer
        # will also interpolate the same way as the genset does.
        assert results.generator_set_result.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[1, 2, 10, 0, 0, 0],
            unit=Unit.MEGA_WATT,
        )

        assert results.generator_set_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[True, True, False, True, True, True],
            unit=Unit.NONE,
        )
        assert isinstance(results.components[0], GenericComponentResult)

        emission_results = results.energy_calculator.evaluate_emissions()

        genset_emissions = emission_results[generator.name]
        assert genset_emissions["co2"].rate.values == [0.001, 0.002, 0.002, 0, 0, 0]
        assert results.generator_set_result.periods == variables.periods

    def test_genset_with_elconsumer_nan_results(self, genset_test_helper, request):
        """Testing what happens when the el-consumers has nan-values in power. -> Genset should not do anything."""
        time_vector = genset_test_helper.time_vector
        variables = VariablesMap(time_vector=time_vector)

        generator = genset_test_helper.genset_2mw(request)
        installation = genset_test_helper.installation(generator, request)
        asset = genset_test_helper.asset(
            installation=installation,
            facility_inputs=[genset_test_helper.generator_fuel_energy_function()],
        )
        resources = {
            genset_test_helper.generator_fuel_energy_function().name: genset_test_helper.generator_el2fuel_2mw_resource(),
        }
        yaml_model = genset_test_helper.get_yaml_model(request, asset, resources)

        generator_set_model = yaml_model.get_graph().get_node(generator.name).generator_set_model

        genset = Genset(
            id=generator.name,
            name=generator.name,
            temporal_generator_set_model=TemporalModel(
                {
                    start_time: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for start_time, model in generator_set_model.items()
                }
            ),
        )

        results = genset.evaluate(
            expression_evaluator=variables,
            power_requirement=TimeSeriesFloat(
                values=[np.nan, np.nan, 0.5, 0.5, np.nan, np.nan],
                periods=variables.get_periods(),
                unit=Unit.MEGA_WATT,
            ),
        )

        # The Genset is not supposed to handle NaN-values from the el-consumers.
        np.testing.assert_equal(results.power.values, [np.nan, np.nan, 0.5, 0.5, np.nan, np.nan])
        assert results.power.unit == Unit.MEGA_WATT
        assert results.power.periods == variables.periods

        # The resulting fuel rate will be zero and the result is invalid for the NaN periods.
        assert results.energy_usage == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[0, 0, 0.6, 0.6, 0.0, 0.0],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        )
        assert results.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[False, False, True, True, False, False],
            unit=Unit.NONE,
        )

    def test_genset_outside_capacity(self, genset_test_helper, request):
        """Testing what happens when the power rate is outside of genset capacity. -> Genset will extrapolate (forward fill)."""
        time_vector = genset_test_helper.time_vector
        variables = VariablesMap(time_vector=time_vector)

        generator = genset_test_helper.genset_2mw(request)
        installation = genset_test_helper.installation(generator, request)
        asset = genset_test_helper.asset(
            installation=installation,
            facility_inputs=[genset_test_helper.generator_fuel_energy_function()],
        )
        resources = {
            genset_test_helper.generator_fuel_energy_function().name: genset_test_helper.generator_el2fuel_2mw_resource(),
        }
        yaml_model = genset_test_helper.get_yaml_model(request, asset, resources)

        generator_set_model = yaml_model.get_graph().get_node(generator.name).generator_set_model
        genset = Genset(
            id=generator.name,
            name=generator.name,
            temporal_generator_set_model=TemporalModel(
                {
                    start_time: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for start_time, model in generator_set_model.items()
                }
            ),
        )

        results = genset.evaluate(
            expression_evaluator=variables,
            power_requirement=TimeSeriesFloat(
                values=[1, 2, 3, 4, 5, 6],
                periods=variables.get_periods(),
                unit=Unit.MEGA_WATT,
            ),
        )

        # The genset will still report power rate
        assert results.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.MEGA_WATT,
        )

        # But the fuel rate will only be valid for the first step. The rest is extrapolated.
        assert results.energy_usage == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[1, 2, 2, 2, 2, 2],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        )
        assert results.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[True, True, False, False, False, False],
            unit=Unit.NONE,
        )

    def test_genset_late_startup(self, genset_test_helper, request):
        time_vector = genset_test_helper.time_vector
        variables = VariablesMap(time_vector=time_vector)

        electricity2fuel = genset_test_helper.generator_fuel_energy_function("1000mw")

        generator = genset_test_helper.genset_1000mw_late_start(request)
        installation = genset_test_helper.installation(generator, request)
        asset = genset_test_helper.asset(installation=installation, facility_inputs=[electricity2fuel])
        resources = {
            electricity2fuel.name: genset_test_helper.generator_el2fuel_1000mw_resource(),
        }
        yaml_model = genset_test_helper.get_yaml_model(request, asset, resources)

        results = genset_test_helper.get_results(yaml_model, variables, generator.name)

        assert results.generator_set_result.power == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[1.0, 2.0, 10.0, 0.0, 0.0, 0.0],
            unit=Unit.MEGA_WATT,
        )

        # Note that the genset is not able to deliver the power rate demanded by the el-consumer(s) for the two
        # first time-steps before the genset is activated in 2022.
        assert results.generator_set_result.energy_usage == TimeSeriesStreamDayRate(
            periods=variables.periods,
            values=[0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        )
        assert results.generator_set_result.is_valid == TimeSeriesBoolean(
            periods=variables.periods,
            values=[False, False, True, True, True, True],
            unit=Unit.NONE,
        )
        np.testing.assert_equal(results.components[0].power.values, [1.0, 2.0, 10.0, 0.0, 0.0, 0.0])
