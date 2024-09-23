from datetime import datetime

import pytest
from pydantic import ValidationError

from libecalc import dto
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.expression import Expression


class TestElectricityConsumer:
    def test_invalid_energy_usage(self):
        with pytest.raises(ValidationError) as e:
            dto.ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={datetime(1900, 1, 1): "MISCELLANEOUS"},
                energy_usage_model={
                    datetime(1900, 1, 1): dto.DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.FUEL
                    )
                },
                regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
            )
        assert "Model does not consume POWER" in str(e.value)

    def test_valid_electricity_consumer(self):
        # Should not raise ValidationError
        dto.ElectricityConsumer(
            name="Test",
            component_type=ComponentType.GENERIC,
            user_defined_category={datetime(1900, 1, 1): "MISCELLANEOUS"},
            energy_usage_model={
                datetime(1900, 1, 1): dto.DirectConsumerFunction(
                    load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                )
            },
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        )
