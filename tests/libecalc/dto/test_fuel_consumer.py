from datetime import datetime
from io import StringIO

import pytest
from yaml import YAMLError

from libecalc.presentation.yaml.validation_errors import DtoValidationError, DataValidationError, ValidationError
from libecalc.presentation.yaml.yaml_models.exceptions import DuplicateKeyError, YamlError
import libecalc.dto.fuel_type
import libecalc.dto.types
from ecalc_cli.types import Frequency
from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure import FuelConsumer, Installation
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.component_validation_error import (
    ComponentValidationException,
    ComponentDtoValidationError,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.testing.yaml_builder import YamlAssetBuilder, YamlInstallationBuilder, YamlFuelConsumerBuilder

regularity = {Period(datetime(2000, 1, 1)): Expression.setup_from_expression(1)}


def get_fuel(fuel_name: str, emission_name: str) -> dict[Period, libecalc.dto.fuel_type.FuelType]:
    """
    Generates a fuel type dto for use in testing

    Args:
        fuel_name: name of fuel
        emission_name: name of emission, e.g. co2

    Returns:
       dict[Period, dto.types.FuelType]
    """
    return {
        Period(datetime(2000, 1, 1)): libecalc.dto.fuel_type.FuelType(
            name=fuel_name,
            emissions=[
                dto.Emission(
                    name=emission_name,
                    factor=Expression.setup_from_expression(value=1),
                ),
            ],
            user_defined_category=dto.types.FuelTypeUserDefinedCategoryType.FUEL_GAS,
        )
    }


def get_installation(installation_name: str, fuel_consumer: FuelConsumer) -> Installation:
    """
    Generates an installation dto for use in testing

    Args:
        installation_name: name of installation
        fuel_consumer: a fuel consumer object, e.g. a generator, compressor or boiler

    Returns:
        dto.Installation
    """
    return Installation(
        name=installation_name,
        regularity=regularity,
        hydrocarbon_export={Period(datetime(1900, 1, 1)): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[fuel_consumer],
        user_defined_category=libecalc.dto.types.InstallationUserDefinedCategoryType.FIXED,
    )


def get_fuel_consumer(
    consumer_name: str,
    fuel_type: dict[Period, libecalc.dto.fuel_type.FuelType],
    category: dict[Period, libecalc.dto.types.ConsumerUserDefinedCategoryType],
) -> FuelConsumer:
    """
    Generates a fuel consumer dto for use in testing

    Args:
        consumer_name: name of fuel consumer
        fuel_type: fuel type, e.g. FUEL_GAS or DIESEL
        category: user defined consumer category

    Returns:
        dto.FuelConsumer
    """
    return FuelConsumer(
        name=consumer_name,
        fuel=fuel_type,
        component_type=ComponentType.GENERIC,
        energy_usage_model={
            Period(datetime(2000, 1, 1)): dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(1),
                energy_usage_type=EnergyUsageType.FUEL,
            )
        },
        regularity=regularity,
        user_defined_category=category,
    )


class TestFuelConsumerHelper:
    def __init__(self):
        self.time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1)]
        self.defined_fuel = "fuel"

    def get_stream(self, consumer_fuel: str, installation_fuel: str = ""):
        fuel_reference = consumer_fuel
        fuel_consumer = YamlFuelConsumerBuilder().with_test_data().with_fuel(fuel_reference).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("Installation 1")
            .with_fuel(installation_fuel)
            .with_fuel_consumers([fuel_consumer])
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_installations([installation])
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
        return ResourceStream(name="", stream=StringIO(yaml_string))


@pytest.fixture()
def test_fuel_consumer_helper():
    return TestFuelConsumerHelper()


class TestFuelConsumer:
    def test_blank_fuel_reference(self, yaml_model_factory, test_fuel_consumer_helper):
        """
        Check scenarios with blank fuel reference.
        The asset has one correctly defined fuel type, named 'fuel'.
        """

        # Blank fuel reference in installation and in consumer
        asset_stream = test_fuel_consumer_helper.get_stream(installation_fuel="", consumer_fuel="")

        with pytest.raises(DataValidationError) as exc_info:
            yaml_model_factory(resource_stream=asset_stream, resources={}, frequency=Frequency.YEAR).validate_for_run()

        assert "Invalid fuel reference ''. Available references: fuel" in str(exc_info.value)

        # Correct fuel reference in installation and blank in consumer.
        # The installation fuel should propagate to the consumer, hence model should validate.
        asset_stream = test_fuel_consumer_helper.get_stream(
            installation_fuel=test_fuel_consumer_helper.defined_fuel, consumer_fuel=""
        )

        yaml_model_factory(resource_stream=asset_stream, resources={}, frequency=Frequency.YEAR).validate_for_run()

    def test_wrong_fuel_reference(self, request, yaml_model_factory, test_fuel_consumer_helper):
        """
        Check wrong fuel reference.
        The asset has one correctly defined fuel type, named 'fuel'.

        A wrong fuel reference can be caused by misspelling or by using a reference that is not defined in the asset FUEL_TYPES.
        """

        asset_stream = test_fuel_consumer_helper.get_stream(
            installation_fuel="wrong_fuel_name", consumer_fuel="wrong_fuel_name"
        )

        with pytest.raises(DataValidationError) as exc_info:
            yaml_model_factory(resource_stream=asset_stream, resources={}, frequency=Frequency.YEAR).validate_for_run()

        assert "Invalid fuel reference 'wrong_fuel_name'. Available references: fuel" in str(exc_info.value)
