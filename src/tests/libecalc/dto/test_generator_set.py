from datetime import datetime

import pytest
from libecalc import dto
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.types import ConsumptionType, EnergyModelType, EnergyUsageType
from libecalc.expression import Expression
from pydantic import ValidationError


class TestGeneratorSetSampled:
    def test_valid(self):
        generator_set_sampled = dto.GeneratorSetSampled(
            headers=["FUEL", "POWER"],
            data=[[0, 0], [1, 2], [2, 4], [3, 6]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )
        assert generator_set_sampled.typ == EnergyModelType.GENERATOR_SET_SAMPLED
        assert generator_set_sampled.headers == ["FUEL", "POWER"]
        assert generator_set_sampled.data == [[0, 0], [1, 2], [2, 4], [3, 6]]

    def test_invalid_headers(self):
        with pytest.raises(ValidationError) as exc_info:
            dto.GeneratorSetSampled(
                headers=["FUEL", "POWAH"],
                data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
            )
        assert "Sampled generator set data should have a 'FUEL' and 'POWER' header" in str(exc_info.value)


class TestGeneratorSet:
    def test_valid(self):
        generator_set_dto = dto.GeneratorSet(
            name="Test",
            user_defined_category={datetime(1900, 1, 1): "MISCELLANEOUS"},
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
                    name="fuel_gas",
                    emissions=[],
                )
            },
        )
        assert generator_set_dto.generator_set_model == {
            datetime(1900, 1, 1): dto.GeneratorSetSampled(
                headers=["FUEL", "POWER"],
                data=[[0, 0], [1, 2], [2, 4], [3, 6]],
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
            )
        }

    def test_genset_should_fail_with_fuel_consumer(self):
        fuel = dto.types.FuelType(
            name="fuel",
            emissions=[],
        )
        fuel_consumer = dto.FuelConsumer(
            name="test",
            fuel={datetime(2000, 1, 1): fuel},
            consumes=ConsumptionType.FUEL,
            component_type=ComponentType.GENERIC,
            energy_usage_model={
                datetime(2000, 1, 1): dto.DirectConsumerFunction(
                    fuel_rate=Expression.setup_from_expression(1),
                    energy_usage_type=EnergyUsageType.FUEL,
                )
            },
            regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
            user_defined_category={datetime(2000, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
        )
        with pytest.raises(ValidationError):
            dto.GeneratorSet(
                name="Test",
                user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
                generator_set_model={},
                regularity={},
                consumers=[fuel_consumer],
                fuel={},
            )

    def test_power_from_shore_wrong_category(self):
        """
        Check that CABLE_LOSS and MAX_USAGE_FROM_SHORE are only allowed if generator set category is POWER-FROM-SHORE
        """

        # Check for CABLE_LOSS
        with pytest.raises(ValueError) as exc_info:
            dto.GeneratorSet(
                name="Test",
                user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.BOILER},
                generator_set_model={},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
                consumers=[],
                fuel={},
                cable_loss=0,
            )

        assert (
            "CABLE_LOSS and MAX_USAGE_FROM_SHORE are only valid for the category POWER-FROM-SHORE, not for BOILER"
        ) in str(exc_info.value)

        # Check for MAX_USAGE_FROM_SHORE
        with pytest.raises(ValueError) as exc_info:
            dto.GeneratorSet(
                name="Test",
                user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.BOILER},
                generator_set_model={},
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
                consumers=[],
                fuel={},
                max_usage_from_shore=20,
            )

        assert (
            "CABLE_LOSS and MAX_USAGE_FROM_SHORE are only valid for the category POWER-FROM-SHORE, not for BOILER"
        ) in str(exc_info.value)
