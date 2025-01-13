from datetime import datetime
from io import StringIO

import pytest

from libecalc.presentation.yaml.validation_errors import DataValidationError
from ecalc_cli.types import Frequency
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.testing.yaml_builder import YamlAssetBuilder, YamlInstallationBuilder, YamlFuelConsumerBuilder


class TestFuelConsumerHelper:
    def __init__(self):
        self.time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1)]
        self.defined_fuel = "fuel"

    def get_stream(self, consumer_fuel: str, installation_fuel: str = None):
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
