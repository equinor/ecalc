from datetime import datetime
from io import StringIO

import pytest

import libecalc.dto.fuel_type
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, Period
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    GeneratorSetHeaderValidationException,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlElectricity2fuelBuilder,
    YamlGeneratorSetBuilder,
    YamlInstallationBuilder,
)


class TestGeneratorSetSampled:
    def test_valid(self, generator_set_helper):
        generator_set_sampled = GeneratorSetModel(
            name="generator_set_sampled",
            resource=generator_set_helper.simple_el2fuel_resource(),
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )
        assert generator_set_sampled.typ == EnergyModelType.GENERATOR_SET_SAMPLED
        assert generator_set_sampled.resource.get_headers() == ["FUEL", "POWER"]
        assert [
            generator_set_sampled.resource.get_column("FUEL"),
            generator_set_sampled.resource.get_column("POWER"),
        ] == [
            [0, 1, 2, 3],  # FUEL column
            [0, 2, 4, 6],  # POWER column
        ]

    def test_invalid_headers(self):
        with pytest.raises(GeneratorSetHeaderValidationException) as exc_info:
            resource = MemoryResource(headers=["FUEL", "POWAH"], data=[[0, 1, 2, 3], [0, 2, 4, 6]])
            GeneratorSetModel(
                name="generator_set_sampled",
                resource=resource,
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
            )
        assert "Sampled generator set data should have a 'FUEL' and 'POWER' header" in str(exc_info.value)


class GeneratorSetHelper:
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

    def simple_el2fuel_resource(self):
        return self.memory_resource_factory(
            headers=["FUEL", "POWER"],
            data=[[0, 1, 2, 3], [0, 2, 4, 6]],
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
def generator_set_helper():
    return GeneratorSetHelper()


class TestGeneratorSet:
    def test_valid(self, generator_set_helper, expression_evaluator_factory):
        expression_evaluator = expression_evaluator_factory.from_periods(periods=[Period(datetime(1900, 1, 1))])
        generator_set_dto = GeneratorSetEnergyComponent(
            path_id=PathID("Test"),
            user_defined_category={Period(datetime(1900, 1, 1)): "MISCELLANEOUS"},
            generator_set_model={
                Period(datetime(1900, 1, 1)): GeneratorSetModel(
                    name="generator_set_sampled",
                    resource=generator_set_helper.simple_el2fuel_resource(),
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                )
            },
            regularity=Regularity(
                expression_evaluator=expression_evaluator,
                target_period=expression_evaluator.get_period(),
                expression_input=1,
            ),
            consumers=[],
            fuel={
                Period(datetime(1900, 1, 1)): libecalc.dto.fuel_type.FuelType(
                    name="fuel_gas",
                    emissions=[],
                )
            },
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=expression_evaluator,
        )
        assert len(list(generator_set_dto.temporal_generator_set_model.items())) == 1
        assert generator_set_dto.temporal_generator_set_model.get_model(
            Period(datetime(1900, 1, 1))
        ) == GeneratorSetModel(
            name="generator_set_sampled",
            resource=generator_set_helper.simple_el2fuel_resource(),
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )

    def test_genset_should_fail_with_fuel_consumer(self, expression_evaluator_factory, direct_expression_model_factory):
        """This validation is done in the dto layer"""
        fuel = libecalc.dto.fuel_type.FuelType(
            name="fuel",
            emissions=[],
        )
        expression_evaluator = expression_evaluator_factory.from_periods(periods=[Period(datetime(2000, 1, 1))])
        fuel_consumer = FuelConsumer(
            path_id=PathID("test"),
            fuel={Period(datetime(2000, 1, 1)): fuel},
            component_type=ComponentType.GENERIC,
            energy_usage_model=TemporalModel(
                {
                    Period(datetime(2000, 1, 1)): direct_expression_model_factory(
                        expression=Expression.setup_from_expression(1),
                        energy_usage_type=EnergyUsageType.FUEL,
                    )
                }
            ),
            user_defined_category={Period(datetime(2000, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
            expression_evaluator=expression_evaluator,
            regularity=Regularity(
                expression_evaluator=expression_evaluator,
                target_period=expression_evaluator.get_period(),
                expression_input=1,
            ),
        )
        with pytest.raises(ComponentValidationException):
            GeneratorSetEnergyComponent(
                path_id=PathID("Test"),
                user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
                generator_set_model={},
                regularity=Regularity(
                    expression_evaluator=expression_evaluator,
                    expression_input=1,
                    target_period=expression_evaluator.get_period(),
                ),
                consumers=[fuel_consumer],
                fuel={},
                component_type=ComponentType.GENERATOR_SET,
                expression_evaluator=expression_evaluator,
            )

    def test_missing_installation_fuel(self, yaml_model_factory, generator_set_helper):
        """
        Check scenario where FUEL is not entered as a keyword in installation.
        In addition, the generator set has an empty fuel reference.

        The error should be handled in the infrastructure layer (dto).
        """

        asset_data = generator_set_helper.get_data(installation_fuel=None, consumer_fuel="")

        with pytest.raises(ModelValidationException) as exc_info:
            yaml_model_factory(
                configuration=asset_data.resource_stream, resources=asset_data.resources, frequency=Frequency.YEAR
            ).validate_for_run()

        assert (
            "Validation error\n\n\tLocation: DefaultGeneratorSet\n\tName: "
            "DefaultGeneratorSet\n\tMessage: Missing fuel for generator set\n"
        ) in str(exc_info.value)
