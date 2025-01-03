from datetime import datetime

import pytest
from pydantic import ValidationError

import libecalc.dto.fuel_type
import libecalc.dto.types
from libecalc import dto
from libecalc.domain.infrastructure import FuelConsumer, Installation
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.component_validation_error import ComponentValidationException
from libecalc.expression import Expression

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


class TestFuelConsumer:
    def test_missing_fuel(self):
        with pytest.raises(ComponentValidationException) as exc_info:
            FuelConsumer(
                name="test",
                fuel={},
                component_type=ComponentType.GENERIC,
                energy_usage_model={
                    Period(datetime(2000, 1, 1)): dto.DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(1),
                        energy_usage_type=EnergyUsageType.FUEL,
                    )
                },
                regularity=regularity,
                user_defined_category="category",
            )
        assert "Name: test\nMessage: Missing fuel for fuel consumer" in str(exc_info.value.errors()[0])
