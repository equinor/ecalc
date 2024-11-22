import pytest
from datetime import datetime
from typing import Optional

from libecalc.common.time_utils import Period
from libecalc.testing.yaml_builder import (
    YamlFuelTypeBuilder,
    YamlFuelConsumerBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlElectricityConsumerBuilder,
)

from libecalc.dto.types import (
    FuelTypeUserDefinedCategoryType,
    ConsumerUserDefinedCategoryType,
)

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)


# Fixtures based on builders:
@pytest.fixture
def fuel_gas():
    def fuel(names: Optional[list[str]] = None, factors: Optional[list[float]] = None):
        if factors is None:
            factors = [1]
        if names is None:
            names = ["co2"]
        return (
            YamlFuelTypeBuilder()
            .with_name("fuel")
            .with_emission_names_and_factors(names=names, factors=factors)
            .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
        ).validate()

    return fuel


@pytest.fixture
def diesel():
    def diesel_fuel(names=None, factors=None):
        if factors is None:
            factors = [1]
        if names is None:
            names = ["co2"]
        return (
            YamlFuelTypeBuilder()
            .with_name("diesel")
            .with_emission_names_and_factors(names=names, factors=factors)
            .with_category(FuelTypeUserDefinedCategoryType.DIESEL)
        ).validate()

    return diesel_fuel


@pytest.fixture
def energy_usage_model_direct():
    def energy_usage_model(rate: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_fuel_rate(rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def energy_usage_model_direct_load():
    def energy_usage_model(load: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_load(load)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def fuel_consumer_direct(energy_usage_model_direct):
    def fuel_consumer(
        fuel_reference_name: str,
        rate: float,
        name: str = "fuel_consumer",
        category: ConsumerUserDefinedCategoryType = ConsumerUserDefinedCategoryType.FLARE,
    ):
        return (
            YamlFuelConsumerBuilder()
            .with_name(name)
            .with_fuel(fuel_reference_name)
            .with_category(category)
            .with_energy_usage_model(energy_usage_model_direct(rate))
        ).validate()

    return fuel_consumer


@pytest.fixture
def fuel_consumer_direct_load(energy_usage_model_direct_load):
    def fuel_consumer(fuel_reference_name: str, load: float):
        return (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_fuel(fuel_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load(load))
        ).validate()

    return fuel_consumer


@pytest.fixture
def el_consumer_direct_base_load(energy_usage_model_direct_load):
    def el_consumer(el_reference_name: str, load: float):
        return (
            YamlElectricityConsumerBuilder()
            .with_name(el_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load(load))
        ).validate()

    return el_consumer
