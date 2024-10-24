from datetime import datetime
from typing import Dict

import pytest
from pydantic import ValidationError

import libecalc.dto.fuel_type
import libecalc.dto.types
from libecalc import dto
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.expression import Expression

regularity = {Period(datetime(2000, 1, 1)): Expression.setup_from_expression(1)}


def get_fuel(fuel_name: str, emission_name: str) -> Dict[Period, libecalc.dto.fuel_type.FuelType]:
    """
    Generates a fuel type dto for use in testing

    Args:
        fuel_name: name of fuel
        emission_name: name of emission, e.g. co2

    Returns:
        Dict[Period, dto.types.FuelType]
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


def get_installation(installation_name: str, fuel_consumer: dto.FuelConsumer) -> dto.Installation:
    """
    Generates an installation dto for use in testing

    Args:
        installation_name: name of installation
        fuel_consumer: a fuel consumer object, e.g. a generator, compressor or boiler

    Returns:
        dto.Installation
    """
    return dto.Installation(
        name=installation_name,
        regularity=regularity,
        hydrocarbon_export={Period(datetime(1900, 1, 1)): Expression.setup_from_expression("sim1;var1")},
        fuel_consumers=[fuel_consumer],
        user_defined_category=libecalc.dto.types.InstallationUserDefinedCategoryType.FIXED,
    )


def get_fuel_consumer(
    consumer_name: str,
    fuel_type: Dict[Period, libecalc.dto.fuel_type.FuelType],
    category: Dict[Period, libecalc.dto.types.ConsumerUserDefinedCategoryType],
) -> dto.FuelConsumer:
    """
    Generates a fuel consumer dto for use in testing

    Args:
        consumer_name: name of fuel consumer
        fuel_type: fuel type, e.g. FUEL_GAS or DIESEL
        category: user defined consumer category

    Returns:
        dto.FuelConsumer
    """
    return dto.FuelConsumer(
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
        with pytest.raises(ValidationError) as exc_info:
            dto.FuelConsumer(
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
        assert "Missing fuel for fuel consumer 'test'" in str(exc_info.value)

    def test_duplicate_fuel_names(self):
        """
        TEST SCOPE: Check that duplicate fuel type names are not allowed.

        Duplicate fuel type names should not be allowed across installations.
        Duplicate names may lead to debug problems and overriding of previous
        values without user noticing. This test checks that different fuels cannot
        have same name.
        """
        fuel_consumer1 = get_fuel_consumer(
            consumer_name="flare",
            fuel_type=get_fuel("fuel1", emission_name="co2"),
            category={Period(datetime(2000, 1, 1)): libecalc.dto.types.ConsumerUserDefinedCategoryType.FLARE},
        )

        fuel_consumer2 = get_fuel_consumer(
            consumer_name="boiler",
            fuel_type=get_fuel("fuel1", emission_name="ch4"),
            category={Period(datetime(2000, 1, 1)): libecalc.dto.types.ConsumerUserDefinedCategoryType.BOILER},
        )

        installation1 = get_installation("INST1", fuel_consumer1)
        installation2 = get_installation("INST2", fuel_consumer2)

        with pytest.raises(ValidationError) as exc_info:
            dto.Asset(
                name="multiple_installations_asset",
                installations=[
                    installation1,
                    installation2,
                ],
            )

        assert "Duplicated names are: fuel1" in str(exc_info.value)

    def test_same_fuel(self):
        """
        TEST SCOPE: Check that validation of duplicate fuel type names do not reject
        when same fuel is used across installations.

        Even though duplicate fuel type names are not allowed across installations,
        it should be possible to reuse the same fuel. This test verifies that this still
        works.
        """

        fuel_consumer1 = get_fuel_consumer(
            consumer_name="flare",
            fuel_type=get_fuel("fuel1", emission_name="co2"),
            category={Period(datetime(2000, 1, 1)): libecalc.dto.types.ConsumerUserDefinedCategoryType.FLARE},
        )

        fuel_consumer2 = get_fuel_consumer(
            consumer_name="boiler",
            fuel_type=get_fuel("fuel1", emission_name="co2"),
            category={Period(datetime(2000, 1, 1)): libecalc.dto.types.ConsumerUserDefinedCategoryType.BOILER},
        )

        installation1 = get_installation("INST1", fuel_consumer1)
        installation2 = get_installation("INST2", fuel_consumer2)

        asset = dto.Asset(
            name="multiple_installations_asset",
            installations=[
                installation1,
                installation2,
            ],
        )
        fuel_types = []
        for inst in asset.installations:
            for fuel_consumer in inst.fuel_consumers:
                for fuel_type in fuel_consumer.fuel.values():
                    if fuel_type not in fuel_types:
                        fuel_types.append(fuel_type)

        assert len(fuel_types) == 1
