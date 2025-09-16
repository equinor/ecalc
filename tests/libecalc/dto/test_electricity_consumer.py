from datetime import datetime
from uuid import uuid4

from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.regularity import Regularity


class TestElectricityConsumer:
    def test_valid_electricity_consumer(self, expression_evaluator_factory, direct_expression_model_factory):
        expression_evaluator = expression_evaluator_factory.from_periods(periods=[Period(datetime(1900, 1, 1))])
        regularity = Regularity(
            expression_evaluator=expression_evaluator,
            expression_input={Period(datetime(1900, 1, 1)): 1},
            target_period=expression_evaluator.get_period(),
        )
        # Should not raise ValidationError
        ElectricityConsumer(
            id=uuid4(),
            name="Test",
            component_type=ComponentType.GENERIC,
            energy_usage_model=TemporalModel(
                {
                    Period(datetime(1900, 1, 1)): direct_expression_model_factory(
                        expression=5,
                        energy_usage_type=EnergyUsageType.POWER,
                        expression_evaluator=expression_evaluator,
                        regularity=regularity,
                    )
                }
            ),
            regularity=regularity,
            expression_evaluator=expression_evaluator,
        )
