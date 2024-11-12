import pytest
from libecalc.testing.yaml_builder import (
    YamlEmissionBuilder,
    YamlFuelTypeBuilder,
    YamlElectricity2fuelBuilder,
    YamlGeneratorSetBuilder,
)

from libecalc.dto.types import FuelTypeUserDefinedCategoryType, ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModelType

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


def test_fuel_emissions(emissions_factory):
    emissions_multi = emissions_factory(
        names=["CO2", "CH4", "NOX", "NMVOC"], factors=[co2_factor, ch4_factor, nox_factor, nmvoc_factor]
    )

    fuel = (
        YamlFuelTypeBuilder()
        .with_name("fuel_turbine")
        .with_emissions(emissions_multi)
        .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
        .validate()
    )

    electricity2fuel = YamlElectricity2fuelBuilder().with_test_data().validate()
    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("genset")
        .with_electricity2fuel(electricity2fuel.name)
        .with_fuel(fuel.name)
        .with_category(ConsumerUserDefinedCategoryType.TURBINE_GENERATOR)
    ).validate()
    genset2 = YamlGeneratorSetBuilder().with_test_data().validate()
    assert fuel
    # installation = YamlInstallationBuilder.with_generator_sets()
    # test = 1
