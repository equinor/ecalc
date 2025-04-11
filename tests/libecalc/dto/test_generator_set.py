from datetime import datetime
from io import StringIO
from typing import Union

import pytest

import libecalc.dto.fuel_type
from libecalc.domain.process import dto
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.component_validation_error import ComponentValidationException, ProcessHeaderValidationException
from libecalc.domain.process.generator_set import GeneratorSetData
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period, Frequency
from libecalc.common.variables import VariablesMap
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream, MemoryResource
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.testing.yaml_builder import (
    YamlGeneratorSetBuilder,
    YamlAssetBuilder,
    YamlInstallationBuilder,
    YamlElectricity2fuelBuilder,
)


class TestGeneratorSetSampled:
    def test_valid(self):
        generator_set_sampled = GeneratorSetData(
            headers=["FUEL", "POWER"],
            data=[[0, 0], [1, 2], [2, 4], [3, 6]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )
        assert generator_set_sampled.typ == EnergyModelType.GENERATOR_SET_SAMPLED
        assert generator_set_sampled.headers == ["FUEL", "POWER"]
        assert generator_set_sampled.data == [[0, 0], [1, 2], [2, 4], [3, 6]]

    def test_invalid_headers(self):
        with pytest.raises(ProcessHeaderValidationException) as exc_info:
            GeneratorSetData(
                headers=["FUEL", "POWAH"],
                data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
            )
        assert "Sampled generator set data should have a 'FUEL' and 'POWER' header" in str(exc_info.value)


class TestGeneratorSetHelper:
    def __init__(self):
        self.time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1)]
        self.defined_fuel = "fuel"

    class ReturnValue:
        def __init__(self, resource_stream: ResourceStream, resources: dict):
            self.resource_stream = resource_stream
            self.resources = resources

    @staticmethod
    def memory_resource_factory(data: list[list[float | int | str]], headers: list[str]) -> MemoryResource:
        return MemoryResource(
            data=data,
            headers=headers,
        )

    def generator_electricity2fuel_resource(self):
        return self.memory_resource_factory(
            data=[
                [
                    0,
                    0.1,
                    10,
                    11,
                    12,
                    14,
                    15,
                    16,
                    17,
                    17.1,
                    18.5,
                    20,
                    20.5,
                    20.6,
                    24,
                    28,
                    30,
                    32,
                    34,
                    36,
                    38,
                    40,
                    41,
                    410,
                ],
                [
                    0,
                    75803.4,
                    75803.4,
                    80759.1,
                    85714.8,
                    95744,
                    100728.8,
                    105676.9,
                    110598.4,
                    136263.4,
                    143260,
                    151004.1,
                    153736.5,
                    154084.7,
                    171429.6,
                    191488,
                    201457.5,
                    211353.8,
                    221196.9,
                    231054,
                    241049.3,
                    251374.6,
                    256839.4,
                    2568394,
                ],
            ],  # float and int with equal value should count as equal.
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    def get_data(self, consumer_fuel: str, installation_fuel: str = None):
        fuel_reference = consumer_fuel
        el2fuel = YamlElectricity2fuelBuilder().with_test_data().validate()
        generator_set = YamlGeneratorSetBuilder().with_test_data().with_fuel(fuel_reference).validate()
        installation = (
            YamlInstallationBuilder()
            .with_name("Installation 1")
            .with_fuel(installation_fuel)
            .with_generator_sets([generator_set])
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_installations([installation])
            .with_facility_inputs([el2fuel])
            .with_start(self.time_vector[0])
            .with_end(self.time_vector[-1])
        ).validate()

        # Set the name of defined fuel type for the asset
        asset.fuel_types[0].name = self.defined_fuel

        asset_dict = asset.model_dump(
            serialize_as_any=True,
            mode="json",
            exclude_unset=True,
            by_alias=True,
        )
        yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)

        resources = {el2fuel.name: self.generator_electricity2fuel_resource()}
        return self.ReturnValue(
            resource_stream=ResourceStream(name="yaml_file_location", stream=StringIO(yaml_string)), resources=resources
        )


@pytest.fixture()
def test_generator_set_helper():
    return TestGeneratorSetHelper()


class TestGeneratorSet:
    def test_valid(self):
        generator_set_dto = GeneratorSetEnergyComponent(
            name="Test",
            user_defined_category={Period(datetime(1900, 1, 1)): "MISCELLANEOUS"},
            generator_set_model={
                Period(datetime(1900, 1, 1)): GeneratorSetData(
                    headers=["FUEL", "POWER"],
                    data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                )
            },
            regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression(1)},
            consumers=[],
            fuel={
                Period(datetime(1900, 1, 1)): libecalc.dto.fuel_type.FuelType(
                    name="fuel_gas",
                    emissions=[],
                )
            },
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=VariablesMap(time_vector=[datetime(1900, 1, 1)]),
        )
        assert generator_set_dto.generator_set_model == {
            Period(datetime(1900, 1, 1)): GeneratorSetData(
                headers=["FUEL", "POWER"],
                data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
            )
        }

    def test_genset_should_fail_with_fuel_consumer(self):
        """This validation is done in the dto layer"""
        fuel = libecalc.dto.fuel_type.FuelType(
            name="fuel",
            emissions=[],
        )
        fuel_consumer = FuelConsumer(
            name="test",
            fuel={Period(datetime(2000, 1, 1)): fuel},
            consumes=ConsumptionType.FUEL,
            component_type=ComponentType.GENERIC,
            energy_usage_model={
                Period(datetime(2000, 1, 1)): dto.DirectConsumerFunction(
                    fuel_rate=Expression.setup_from_expression(1),
                    energy_usage_type=EnergyUsageType.FUEL,
                )
            },
            regularity={Period(datetime(2000, 1, 1)): Expression.setup_from_expression(1)},
            user_defined_category={Period(datetime(2000, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
            expression_evaluator=VariablesMap(time_vector=[datetime(2000, 1, 1)]),
        )
        with pytest.raises(ComponentValidationException):
            GeneratorSetEnergyComponent(
                name="Test",
                user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
                generator_set_model={},
                regularity={},
                consumers=[fuel_consumer],
                fuel={},
                component_type=ComponentType.GENERATOR_SET,
                expression_evaluator=VariablesMap(time_vector=[datetime(1900, 1, 1)]),
            )

    def test_missing_installation_fuel(self, yaml_model_factory, test_generator_set_helper):
        """
        Check scenario where FUEL is not entered as a keyword in installation.
        In addition, the generator set has an empty fuel reference.

        The error should be handled in the infrastructure layer (dto).
        """

        asset_data = test_generator_set_helper.get_data(installation_fuel=None, consumer_fuel="")

        with pytest.raises(ModelValidationException) as exc_info:
            yaml_model_factory(
                resource_stream=asset_data.resource_stream, resources=asset_data.resources, frequency=Frequency.YEAR
            ).validate_for_run()

        assert (
            "Validation error\n\n\tLocation: DefaultGeneratorSet\n\tName: "
            "DefaultGeneratorSet\n\tMessage: Missing fuel for generator set\n"
        ) in str(exc_info.value)
