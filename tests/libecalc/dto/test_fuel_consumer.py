from datetime import datetime
from io import StringIO
from uuid import uuid4

import pytest
from inline_snapshot import snapshot

import libecalc
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlFuelConsumerBuilder,
    YamlInstallationBuilder,
)


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

    @staticmethod
    def fuel(name: str, co2_factor: float) -> libecalc.dto.fuel_type.FuelType:
        """Creates a simple fuel type object for use in fuel consumer setup
        Args:
            name (str): Name of fuel
            co2_factor (str): CO2 factor used for emission calculations

        Returns:
            dto.types.FuelType
        """

        return libecalc.dto.fuel_type.FuelType(
            id=uuid4(),
            name=name,
            emissions=[
                Emission(
                    name="co2",
                    factor=Expression.setup_from_expression(value=co2_factor),
                )
            ],
            user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS,
        )


@pytest.fixture()
def test_fuel_consumer_helper():
    return TestFuelConsumerHelper()


class TestFuelConsumer:
    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_no_fuel_installation_and_blank_reference_consumer(self, yaml_model_factory, test_fuel_consumer_helper):
        """
        Check scenario where FUEL is not entered as a keyword in installation.
        In addition, the consumer has a blank fuel reference.

        The error should be handled in the infrastructure layer (dto).
        """

        asset_stream = test_fuel_consumer_helper.get_stream(installation_fuel=None, consumer_fuel="")

        with pytest.raises(ModelValidationException) as exc_info:
            yaml_model_factory(configuration=asset_stream, resources={}, frequency=Frequency.YEAR).validate_for_run()

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 13
	Location: installations.Installation 1.FUELCONSUMERS.flare.fuel
	Name: flare
	Message: Missing fuel reference
""")

    def test_negative_fuel_rate_direct_fuel_consumer(
        self, test_fuel_consumer_helper, expression_evaluator_factory, direct_expression_model_factory
    ):
        fuel = test_fuel_consumer_helper.fuel(name="fuel", co2_factor=1)
        period1 = Period(datetime(2027, 1, 1), datetime(2028, 1, 1))
        period2 = Period(datetime(2028, 1, 1), datetime(2029, 1, 1))
        periods = Periods([period1, period2])
        expression_evaluator = expression_evaluator_factory.from_periods_obj(periods=periods)

        negative_fuel = -1
        positive_fuel = 1
        regularity = Regularity(
            expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period()
        )
        energy_usage_model = TemporalModel(
            {
                period: direct_expression_model_factory(
                    expression=expr,
                    energy_usage_type=EnergyUsageType.FUEL,
                    expression_evaluator=expression_evaluator.get_subset(
                        *period.get_period_indices(expression_evaluator.get_periods())
                    ),
                    regularity=regularity.get_subset(*period.get_period_indices(expression_evaluator.get_periods())),
                )
                for period, expr in zip([period1, period2], [negative_fuel, positive_fuel])
            }
        )
        consumer_results = FuelConsumerComponent(
            id=uuid4(),
            path_id=PathID("Test"),
            component_type=ComponentType.GENERIC,
            energy_usage_model=energy_usage_model,
            regularity=regularity,
            expression_evaluator=expression_evaluator,
            fuel={periods.period: fuel},
        ).evaluate_energy_usage(context="")

        # Negative fuel rate is invalid:
        assert not consumer_results["Test"].component_result.is_valid.values[0]

        # Positive fuel rate is valid:
        assert consumer_results["Test"].component_result.is_valid.values[1]
