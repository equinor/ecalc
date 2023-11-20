import typing
from datetime import datetime

import pytest
from libecalc import dto
from libecalc.dto.components import (
    ComponentType,
    ConsumerUserDefinedCategoryType,
    EmitterModel,
    InstallationUserDefinedCategoryType,
)
from libecalc.dto.types import EnergyUsageType, FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from pydantic import ValidationError


class TestCategories:
    def test_direct_emitter_categories(self):
        emitter_model = EmitterModel(
            regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
            emission_rate=Expression.setup_from_expression(4),
        )

        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.DirectEmitter(
                name="test",
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                emission_name="CH4",
                emitter_model={datetime(2000, 1, 1): emitter_model},
                user_defined_category={datetime(2000, 1, 1): "DIRECT-EMISSIONS"},
            )
        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: DIRECT-EMISSIONS is not allowed for DirectEmitter with the name test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.DirectEmitter(
                name="test",
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                emission_name="CH4",
                emitter_model={datetime(2000, 1, 1): emitter_model},
                user_defined_category={datetime(2000, 1, 1): "fuel-gas"},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: fuel-gas is not allowed for DirectEmitter with the name test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.DirectEmitter(
                name="test",
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                emission_name="CH4",
                emitter_model={datetime(2000, 1, 1): emitter_model},
                user_defined_category={datetime(2000, 1, 1): ""},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY:  is not allowed for DirectEmitter with the name test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that underscore raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.DirectEmitter(
                name="test",
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                emission_name="CH4",
                emitter_model={datetime(2000, 1, 1): emitter_model},
                user_defined_category={datetime(2000, 1, 1): "FUEL_GAS"},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: FUEL_GAS is not allowed for DirectEmitter with the name test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that correct category is ok
        assert (
            dto.components.DirectEmitter(
                name="test",
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                emission_name="CH4",
                emitter_model={datetime(2000, 1, 1): emitter_model},
                user_defined_category={datetime(2000, 1, 1): ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE},
            ).user_defined_category[datetime(2000, 1, 1)]
            == ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE
        )

    def test_fuel_type_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.types.FuelType(name="test", user_defined_category="GASOLINE")

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: GASOLINE is not allowed for FuelType with the name test. Valid categories are: ['FUEL-GAS', 'DIESEL']"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.types.FuelType(name="test", user_defined_category="diesel")

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: diesel is not allowed for FuelType with the name test. Valid categories are: ['FUEL-GAS', 'DIESEL']"
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.types.FuelType(name="test", user_defined_category="")
        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY:  is not allowed for FuelType with the name test. Valid categories are: ['FUEL-GAS', 'DIESEL']"
        )

        # Check that underscore raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.types.FuelType(name="test", user_defined_category="FUEL_GAS")

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: FUEL_GAS is not allowed for FuelType with the name test. Valid categories are: ['FUEL-GAS', 'DIESEL']"
        )

        # Check that correct category 1 is ok
        assert (
            dto.types.FuelType(
                name="test", user_defined_category=FuelTypeUserDefinedCategoryType.DIESEL
            ).user_defined_category
            == FuelTypeUserDefinedCategoryType.DIESEL
        )

        # Check that correct category 2 is ok
        assert (
            dto.types.FuelType(
                name="test", user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS
            ).user_defined_category
            == FuelTypeUserDefinedCategoryType.FUEL_GAS
        )

        # Check that not defining category is ok
        assert dto.types.FuelType(name="test").user_defined_category is None

    def test_installation_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.Installation(
                name="test",
                user_defined_category="PLATFORM",
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: PLATFORM is not allowed for Installation with the name test. Valid categories are: ['FIXED', 'MOBILE']"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.Installation(
                name="test",
                user_defined_category="fixed",
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: fixed is not allowed for Installation with the name test. Valid categories are: ['FIXED', 'MOBILE']"
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.components.Installation(
                name="test",
                user_defined_category="",
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY:  is not allowed for Installation with the name test. Valid categories are: ['FIXED', 'MOBILE']"
        )

        # Check that correct category 1 is ok
        assert (
            dto.components.Installation(
                name="test",
                user_defined_category=InstallationUserDefinedCategoryType.MOBILE,
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            ).user_defined_category
            == InstallationUserDefinedCategoryType.MOBILE
        )

        # Check that correct category 2 is ok
        assert (
            dto.components.Installation(
                name="test",
                user_defined_category=InstallationUserDefinedCategoryType.FIXED,
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            ).user_defined_category
            == InstallationUserDefinedCategoryType.FIXED
        )

        # Check that not defining category is ok
        assert (
            dto.components.Installation(
                name="test",
                hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(0)},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            ).user_defined_category
            is None
        )

    def test_el_consumer_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={datetime(1900, 1, 1): "HUGE-SINGLE-SPEED-PUMP"},
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: HUGE-SINGLE-SPEED-PUMP is not allowed for ElectricityConsumer with the name Test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check correct category single date
        assert (
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP},
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            ).user_defined_category[datetime(1900, 1, 1)]
            == ConsumerUserDefinedCategoryType.PUMP
        )

        # Check that empty raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={datetime(1900, 1, 1): ""},
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY:  is not allowed for ElectricityConsumer with the name Test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that not defining category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert exception.errors()[0]["msg"] == "field required"

        # Check correct category multiple dates
        test = dto.ElectricityConsumer(
            name="Test",
            component_type=ComponentType.GENERIC,
            user_defined_category={
                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP,
                datetime(1920, 1, 1): ConsumerUserDefinedCategoryType.PUMP,
                datetime(1940, 1, 1): ConsumerUserDefinedCategoryType.PUMP,
            },
            energy_usage_model={
                datetime(1900, 1, 1): dto.DirectConsumerFunction(
                    load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                )
            },
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        )

        assert test.user_defined_category[datetime(1900, 1, 1)] == ConsumerUserDefinedCategoryType.PUMP
        assert test.user_defined_category[datetime(1920, 1, 1)] == ConsumerUserDefinedCategoryType.PUMP
        assert test.user_defined_category[datetime(1940, 1, 1)] == ConsumerUserDefinedCategoryType.PUMP

        # Check correct multiple categories and multiple dates
        test = dto.ElectricityConsumer(
            name="Test",
            component_type=ComponentType.GENERIC,
            user_defined_category={
                datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP,
                datetime(1920, 1, 1): ConsumerUserDefinedCategoryType.COMPRESSOR,
                datetime(1940, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
            },
            energy_usage_model={
                datetime(1900, 1, 1): dto.DirectConsumerFunction(
                    load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                )
            },
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        )

        assert test.user_defined_category[datetime(1900, 1, 1)] == ConsumerUserDefinedCategoryType.PUMP
        assert test.user_defined_category[datetime(1920, 1, 1)] == ConsumerUserDefinedCategoryType.COMPRESSOR
        assert test.user_defined_category[datetime(1940, 1, 1)] == ConsumerUserDefinedCategoryType.MISCELLANEOUS

        # Check multiple categories and multiple dates, some are correct, some are wrong
        # Should raise error
        with pytest.raises(ValidationError) as exc_info:
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={
                    datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.PUMP,
                    datetime(1920, 1, 1): "FIRST-COMPRESSOR",
                    datetime(1940, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                },
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: FIRST-COMPRESSOR is not allowed for ElectricityConsumer with the name Test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

    def test_genset_categories(self):
        # Check that illegal category raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.GeneratorSet(
                name="Test",
                user_defined_category={datetime(1900, 1, 1): "GENERATOR-SET"},
                generator_set_model={
                    datetime(1900, 1, 1): dto.GeneratorSetSampled(
                        headers=["FUEL", "POWER"],
                        data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                        energy_usage_adjustment_constant=0.0,
                        energy_usage_adjustment_factor=1.0,
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
                consumers=[],
                fuel={
                    datetime(1900, 1, 1): dto.types.FuelType(
                        name="fuel-gas",
                        emissions=[],
                    )
                },
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: GENERATOR-SET is not allowed for GeneratorSet with the name Test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check that lower case raises error
        with pytest.raises(ValidationError) as exc_info:
            dto.GeneratorSet(
                name="Test",
                user_defined_category={datetime(1900, 1, 1): "turbine-generator"},
                generator_set_model={
                    datetime(1900, 1, 1): dto.GeneratorSetSampled(
                        headers=["FUEL", "POWER"],
                        data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                        energy_usage_adjustment_constant=0.0,
                        energy_usage_adjustment_factor=1.0,
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
                consumers=[],
                fuel={
                    datetime(1900, 1, 1): dto.types.FuelType(
                        name="fuel-gas",
                        emissions=[],
                    )
                },
            )

        exception: ValidationError = typing.cast(ValidationError, exc_info.value)
        assert (
            exception.errors()[0]["msg"]
            == "CATEGORY: turbine-generator is not allowed for GeneratorSet with the name Test. Valid categories are: ['BASE-LOAD', 'COLD-VENTING-FUGITIVE', 'COMPRESSOR', 'FIXED-PRODUCTION-LOAD', 'FLARE', 'MISCELLANEOUS', 'PUMP', 'GAS-DRIVEN-COMPRESSOR', 'TURBINE-GENERATOR', 'POWER-FROM-SHORE', 'OFFSHORE-WIND', 'LOADING', 'STORAGE', 'STEAM-TURBINE-GENERATOR', 'BOILER', 'HEATER']"
        )

        # Check correct category
        generator_set_dto = dto.GeneratorSet(
            name="Test",
            user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR},
            generator_set_model={
                datetime(1900, 1, 1): dto.GeneratorSetSampled(
                    headers=["FUEL", "POWER"],
                    data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                )
            },
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            consumers=[],
            fuel={
                datetime(1900, 1, 1): dto.types.FuelType(
                    name="fuel-gas",
                    emissions=[],
                )
            },
        )

        assert (
            generator_set_dto.user_defined_category[datetime(1900, 1, 1)]
            == ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
        )
