from datetime import datetime
from io import StringIO

import pytest

from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
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
    def test_no_fuel_installation_and_blank_reference_consumer(self, yaml_model_factory, test_fuel_consumer_helper):
        """
        Check scenario where FUEL is not entered as a keyword in installation.
        In addition, the consumer has a blank fuel reference.

        The error should be handled in the infrastructure layer (dto).
        """

        asset_stream = test_fuel_consumer_helper.get_stream(installation_fuel=None, consumer_fuel="")

        with pytest.raises(ModelValidationException) as exc_info:
            yaml_model_factory(resource_stream=asset_stream, resources={}, frequency=Frequency.YEAR).validate_for_run()

        assert (
            "Validation error\n\n\tLocation: flare\n\tName: flare\n\t" "Message: Missing fuel for fuel consumer\n"
        ) in str(exc_info.value)
