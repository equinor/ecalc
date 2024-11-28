import pytest
from typing import Optional, Union

from libecalc.presentation.yaml.yaml_entities import MemoryResource
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


def memory_resource_factory(data: list[list[Union[float, int, str]]], headers: list[str]) -> MemoryResource:
    return MemoryResource(
        data=data,
        headers=headers,
    )


# Memory resources
@pytest.fixture
def generator_electricity2fuel_17MW_resource():
    return memory_resource_factory(
        data=[
            [0, 0.1, 10, 11, 12, 14, 15, 16, 17, 17.1, 18.5, 20, 20.5, 20.6, 24, 28, 30, 32, 34, 36, 38, 40, 41, 410],
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


@pytest.fixture
def onshore_power_electricity2fuel_resource():
    return memory_resource_factory(
        data=[
            [0, 10, 20],
            [0, 0, 0],
        ],  # float and int with equal value should count as equal.
        headers=[
            "POWER",
            "FUEL",
        ],
    )


@pytest.fixture
def cable_loss_time_series_resource():
    return memory_resource_factory(
        data=[
            [
                "01.01.2021",
                "01.01.2022",
                "01.01.2023",
                "01.01.2024",
                "01.01.2025",
                "01.01.2026",
                "01.01.2027",
                "01.01.2028",
                "01.01.2029",
                "01.01.2030",
            ],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],  # float and int with equal value should count as equal.
        headers=[
            "DATE",
            "CABLE_LOSS_FACTOR",
        ],
    )


@pytest.fixture
def max_usage_from_shore_time_series_resource():
    return memory_resource_factory(
        data=[
            [
                "01.01.2021",
                "01.01.2022",
                "01.01.2023",
                "01.01.2024",
                "01.01.2025",
                "01.01.2026",
                "01.01.2027",
                "01.01.2028",
                "01.01.2029",
                "01.01.2030",
            ],
            [283, 283, 283, 283, 283, 250, 290, 283, 283, 283],
        ],  # float and int with equal value should count as equal.
        headers=[
            "DATE",
            "MAX_USAGE_FROM_SHORE",
        ],
    )


@pytest.fixture
def compressor_sampled_fuel_driven_resource():
    def compressor(power_compressor_mw: Optional[float] = 3, compressor_rate: Optional[float] = 3000000):
        return memory_resource_factory(
            data=[
                [0.0, 1.0, 2.0, power_compressor_mw, 4.0],
                [0, 10000, 11000, 12000, 13000],
                [0, 1000000, 2000000, compressor_rate, 4000000],
            ],  # float and int with equal value should count as equal.
            headers=["POWER", "FUEL", "RATE"],
        )

    return compressor


@pytest.fixture
def generator_diesel_power_to_fuel_resource():
    def generator(power_usage_mw: Optional[float] = 10, diesel_rate: Optional[float] = 120000):
        return memory_resource_factory(
            data=[
                [0, power_usage_mw, 15, 20],
                [0, diesel_rate, 145000, 160000],
            ],  # float and int with equal value should count as equal.
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    return generator


@pytest.fixture
def generator_fuel_power_to_fuel_resource():
    def generator(power_usage_mw: Optional[float] = 10, fuel_rate: Optional[float] = 67000):
        return memory_resource_factory(
            data=[
                [0, 2.5, 5, power_usage_mw, 15, 20],
                [0, 30000, 45000, fuel_rate, 87000, 110000],
            ],  # float and int with equal value should count as equal.
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    return generator


# Fixtures based on builders:
@pytest.fixture
def fuel_gas_factory():
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
def diesel_factory():
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
def energy_usage_model_direct_factory():
    def energy_usage_model(rate: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_fuel_rate(rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def energy_usage_model_direct_load_factory():
    def energy_usage_model(load: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_load(load)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def fuel_consumer_direct_factory(energy_usage_model_direct_factory):
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
            .with_energy_usage_model(energy_usage_model_direct_factory(rate))
        ).validate()

    return fuel_consumer


@pytest.fixture
def fuel_consumer_direct_load_factory(energy_usage_model_direct_load_factory):
    def fuel_consumer(fuel_reference_name: str, load: float):
        return (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_fuel(fuel_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load_factory(load))
        ).validate()

    return fuel_consumer


@pytest.fixture
def el_consumer_direct_base_load_factory(energy_usage_model_direct_load_factory):
    def el_consumer(el_reference_name: str, load: float):
        return (
            YamlElectricityConsumerBuilder()
            .with_name(el_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load_factory(load))
        ).validate()

    return el_consumer
