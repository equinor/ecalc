from datetime import datetime

import pytest

from libecalc import dto
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure import ElectricityConsumer
from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.component_validation_error import ComponentValidationException
from libecalc.expression import Expression


class TestElectricityConsumer:
    def test_invalid_energy_usage(self):
        with pytest.raises(ComponentValidationException) as e:
            ElectricityConsumer(
                name="Test",
                component_type=ComponentType.GENERIC,
                user_defined_category={Period(datetime(1900, 1, 1)): "MISCELLANEOUS"},
                energy_usage_model={
                    Period(datetime(1900, 1, 1)): dto.DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.FUEL
                    )
                },
                regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression(1)},
                expression_evaluator=VariablesMap(time_vector=[datetime(1900, 1, 1)]),
            )
        assert "Model does not consume POWER" in str(e.value.errors()[0])

    def test_valid_electricity_consumer(self):
        # Should not raise ValidationError
        ElectricityConsumer(
            name="Test",
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): "MISCELLANEOUS"},
            energy_usage_model={
                Period(datetime(1900, 1, 1)): dto.DirectConsumerFunction(
                    load=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                )
            },
            regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression(1)},
            expression_evaluator=VariablesMap(time_vector=[datetime(1900, 1, 1)]),
        )
