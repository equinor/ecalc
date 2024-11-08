import pytest
from yaml_builder import YamlEmissionBuilder, YamlFuelTypeBuilder

from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission

co2_factor = 1
ch4_factor = 0.1
nox_factor = 0.5
nmvoc_factor = 0


@pytest.fixture
def emissions_factory():
    def emissions(names: list[str], factors: list[float]):
        emissions_list = []
        for name, factor in zip(names, factors):
            emissions_list.append(YamlEmissionBuilder().with_name(name=name).with_factor(factor=factor).validate())
        return emissions_list

    return emissions


@pytest.fixture
def fuel_factory():
    def fuel(name: str, emissions: list[YamlEmission], category: FuelTypeUserDefinedCategoryType):
        fuel = YamlFuelTypeBuilder().with_name(name=name)
        fuel.category = category
        fuel.emissions = emissions
        return fuel.validate()

    return fuel


def test_fuel_emissions(emissions_factory, fuel_factory):
    emissions_multi = emissions_factory(
        names=["CO2", "CH4", "NOX", "NMVOC"], factors=[co2_factor, ch4_factor, nox_factor, nmvoc_factor]
    )
    fuel = fuel_factory(
        name="fuel_turbine", emissions=emissions_multi, category=FuelTypeUserDefinedCategoryType.FUEL_GAS
    )
    assert fuel
    # installation = YamlInstallationBuilder.with_generator_sets()
    # test = 1
