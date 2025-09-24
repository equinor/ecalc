from datetime import datetime
from io import StringIO
from uuid import uuid4

import pytest
from inline_snapshot import snapshot

import libecalc.dto.fuel_type
from libecalc.common.component_type import ComponentType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, Period
from libecalc.domain.component_validation_error import (
    GeneratorSetHeaderValidationException,
)
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.regularity import Regularity
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlElectricity2fuelBuilder,
    YamlFuelTypeBuilder,
    YamlGeneratorSetBuilder,
    YamlInstallationBuilder,
)


class TestGeneratorSetSampled:
    def test_valid(self, test_generator_set_helper):
        generator_set_sampled = GeneratorSetModel(
            name="generator_set_sampled",
            resource=test_generator_set_helper.simple_el2fuel_resource(),
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )
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
            .with_fuel_types([YamlFuelTypeBuilder().with_test_data().with_name(self.defined_fuel).validate()])
            .with_installations([installation])
            .with_facility_inputs([el2fuel])
            .with_start(self.time_vector[0])
            .with_end(self.time_vector[-1])
        ).validate()

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
    def test_valid(self, test_generator_set_helper, expression_evaluator_factory):
        expression_evaluator = expression_evaluator_factory.from_periods(periods=[Period(datetime(1900, 1, 1))])
        generator_set_dto = GeneratorSetEnergyComponent(
            id=uuid4(),
            name="Test",
            generator_set_model=TemporalModel(
                {
                    Period(datetime(1900, 1, 1)): GeneratorSetModel(
                        name="generator_set_sampled",
                        resource=test_generator_set_helper.simple_el2fuel_resource(),
                        energy_usage_adjustment_constant=0.0,
                        energy_usage_adjustment_factor=1.0,
                    )
                }
            ),
            regularity=Regularity(
                expression_evaluator=expression_evaluator,
                target_period=expression_evaluator.get_period(),
                expression_input=1,
            ),
            consumers=[],
            fuel=TemporalModel(
                {
                    Period(datetime(1900, 1, 1)): libecalc.dto.fuel_type.FuelType(
                        id=uuid4(),
                        name="fuel_gas",
                        emissions=[],
                    )
                }
            ),
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=expression_evaluator,
        )
        assert len(list(generator_set_dto.temporal_generator_set_model.items())) == 1
        assert generator_set_dto.temporal_generator_set_model.get_model(
            Period(datetime(1900, 1, 1))
        ) == GeneratorSetModel(
            name="generator_set_sampled",
            resource=test_generator_set_helper.simple_el2fuel_resource(),
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    def test_missing_installation_fuel(self, yaml_model_factory, test_generator_set_helper):
        """
        Check scenario where FUEL is not entered as a keyword in installation.
        In addition, the generator set has an empty fuel reference.

        The error should be handled in the infrastructure layer (dto).
        """

        asset_data = test_generator_set_helper.get_data(installation_fuel=None, consumer_fuel="")

        with pytest.raises(ModelValidationException) as exc_info:
            yaml_model_factory(
                configuration=asset_data.resource_stream, resources=asset_data.resources, frequency=Frequency.YEAR
            ).validate_for_run()

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 18
	Location: installations.Installation 1.GENERATORSETS.DefaultGeneratorSet.fuel
	Message: Missing fuel reference
""")
