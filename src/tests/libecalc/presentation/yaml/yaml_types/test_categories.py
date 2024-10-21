from datetime import datetime

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from libecalc.common.utils.rates import RateType
from libecalc.dto.types import (
    ConsumerUserDefinedCategoryType,
    FuelTypeUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import YamlEnergyUsageModelDirect
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlVentingEmission,
    YamlVentingType,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlEmissionRateUnits,
)


def get_category_error(e: ValidationError) -> str:
    for error in e.errors():
        if "category" in error["loc"] or "CATEGORY" in error["loc"]:
            return error["msg"]


def create_direct_energy_usage_model() -> YamlEnergyUsageModelDirect:
    return YamlEnergyUsageModelDirect(
        type="DIRECT",
        load=1,
    )


def create_valid_fuel_consumer() -> YamlFuelConsumer:
    return YamlFuelConsumer(
        name="dummy",
        category="BASE-LOAD",
        energy_usage_model=create_direct_energy_usage_model(),
        fuel="fuel",
    )


class TestCategories:
    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_venting_emitter_categories(self):
        emission = YamlVentingEmission(
            name="CH4",
            rate=YamlEmissionRate(value=4, type=RateType.STREAM_DAY, unit=YamlEmissionRateUnits.KILO_PER_DAY),
        )

        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlDirectTypeEmitter(
                name="test",
                emissions=[emission],
                category="VENTING-EMISSIONS",
                type=YamlVentingType.DIRECT_EMISSION.name,
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Value error, CATEGORY VENTING-EMISSIONS is not allowed for VentingEmitter with the name test. Valid categories are: BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlDirectTypeEmitter(
                name="test",
                emissions=[emission],
                category="fuel-gas",
                type=YamlVentingType.DIRECT_EMISSION.name,
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Value error, CATEGORY fuel-gas is not allowed for VentingEmitter with the name test. Valid categories are: BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER"
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlDirectTypeEmitter(
                name="test",
                emissions=[emission],
                category="",
                type=YamlVentingType.DIRECT_EMISSION.name,
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Value error, CATEGORY  is not allowed for VentingEmitter with the name test. Valid categories are: BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER"
        )

        # Check that underscore raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlDirectTypeEmitter(
                name="test",
                emissions=[emission],
                category="FUEL_GAS",
                type=YamlVentingType.DIRECT_EMISSION.name,
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Value error, CATEGORY FUEL_GAS is not allowed for VentingEmitter with the name test. Valid categories are: BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER"
        )

        # Check that correct category is ok
        assert (
            YamlDirectTypeEmitter(
                name="test",
                emissions=[emission],
                category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
                type=YamlVentingType.DIRECT_EMISSION.name,
            ).category
            == ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE
        )

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_fuel_type_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlFuelType(name="test", category="GASOLINE")

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FUEL-GAS' or 'DIESEL'")

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlFuelType(name="test", category="diesel")

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FUEL-GAS' or 'DIESEL'")

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlFuelType(name="test", category="")

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FUEL-GAS' or 'DIESEL'")

        # Check that underscore raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlFuelType(name="test", category="FUEL_GAS")

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FUEL-GAS' or 'DIESEL'")

        # Check that correct category 1 is ok
        assert (
            YamlFuelType(name="test", category=FuelTypeUserDefinedCategoryType.DIESEL, emissions=[]).category
            == FuelTypeUserDefinedCategoryType.DIESEL
        )

        # Check that correct category 2 is ok
        assert (
            YamlFuelType(name="test", category=FuelTypeUserDefinedCategoryType.FUEL_GAS, emissions=[]).category
            == FuelTypeUserDefinedCategoryType.FUEL_GAS
        )

        # Check that not defining category is ok
        assert YamlFuelType(name="test", emissions=[]).category is None

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_installation_categories(self):
        # Installation-dto requires either fuelconsumers or venting emitters to be set, hence use dummy fuelconsumer:

        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlInstallation(
                name="test",
                category="PLATFORM",
            )

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FIXED' or 'MOBILE'")

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlInstallation(
                name="test",
                category="fixed",
            )

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FIXED' or 'MOBILE'")

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlInstallation(
                name="test",
                category="",
            )

        assert str(get_category_error(exc_info.value)) == snapshot("Input should be 'FIXED' or 'MOBILE'")

        fuel_consumer = create_valid_fuel_consumer()

        # Check that correct category 1 is ok
        assert (
            YamlInstallation(
                name="test",
                category=InstallationUserDefinedCategoryType.MOBILE,
                fuel_consumers=[fuel_consumer],
            ).category
            == InstallationUserDefinedCategoryType.MOBILE
        )

        # Check that correct category 2 is ok
        assert (
            YamlInstallation(
                name="test",
                category=InstallationUserDefinedCategoryType.FIXED,
                fuel_consumers=[fuel_consumer],
            ).category
            == InstallationUserDefinedCategoryType.FIXED
        )

        # Check that not defining category is ok
        assert (
            YamlInstallation(
                name="test",
                fuel_consumers=[fuel_consumer],
            ).category
            is None
        )

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_el_consumer_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlElectricityConsumer(
                name="Test",
                category="HUGE-SINGLE-SPEED-PUMP",
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Input should be 'BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER' or 'HEATER'"
        )

        # Check correct category single date
        assert (
            YamlElectricityConsumer(
                name="Test",
                category=ConsumerUserDefinedCategoryType.PUMP,
                energy_usage_model=create_direct_energy_usage_model(),
            ).category
            == ConsumerUserDefinedCategoryType.PUMP
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlElectricityConsumer(
                name="Test",
                category=None,
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Input should be 'BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER' or 'HEATER'"
        )

        # Check that not defining category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlElectricityConsumer(
                name="Test",
            )

        assert str(get_category_error(exc_info.value)) == snapshot("Field required")

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_genset_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlGeneratorSet(
                name="Test",
                category={datetime(1900, 1, 1): "GENERATOR-SET"},
                electricity2fuel="dummy",
                consumers=[],
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Input should be 'BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER' or 'HEATER'"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            YamlGeneratorSet(
                name="Test",
                category={datetime(1900, 1, 1): "turbine-generator"},
                electricity2fuel="dummy",
                consumers=[],
            )

        assert str(get_category_error(exc_info.value)) == snapshot(
            "Input should be 'BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER' or 'HEATER'"
        )

        # Check correct category
        generator_set_dto = YamlGeneratorSet(
            name="Test",
            category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
            electricity2fuel="dummy",
            consumers=[],
        )

        assert generator_set_dto.category[datetime(1900, 1, 1)] == ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
