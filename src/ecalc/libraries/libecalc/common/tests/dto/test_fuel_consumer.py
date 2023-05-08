from datetime import datetime

import pytest
from libecalc import dto
from libecalc.dto.base import ComponentType
from libecalc.dto.types import EnergyUsageType
from libecalc.expression import Expression
from pydantic import ValidationError


class TestFuelConsumer:
    def test_missing_fuel(self):
        with pytest.raises(ValidationError) as exc_info:
            dto.FuelConsumer(
                name="test",
                fuel={},
                component_type=ComponentType.GENERIC,
                energy_usage_model={
                    datetime(2000, 1, 1): dto.DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(1),
                        energy_usage_type=EnergyUsageType.FUEL,
                    )
                },
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                user_defined_category="category",
            )
        assert "Missing fuel for fuel consumer 'test'" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            dto.FuelConsumer(
                name="test",
                fuel={},
                component_type=ComponentType.GENERIC,
                energy_usage_model={
                    datetime(2000, 1, 1): dto.DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(1),
                        energy_usage_type=EnergyUsageType.FUEL,
                    )
                },
                regularity={datetime(2000, 1, 1): Expression.setup_from_expression(1)},
                user_defined_category="category",
            )
        assert "Missing fuel for fuel consumer 'test'" in str(exc_info.value)
