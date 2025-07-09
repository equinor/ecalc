from datetime import datetime
from uuid import uuid4

from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression


class TestElectricityConsumer:
    def test_valid_electricity_consumer(self, expression_evaluator_factory, direct_expression_model_factory):
        expression_evaluator = expression_evaluator_factory.from_periods(periods=[Period(datetime(1900, 1, 1))])

        # Should not raise ValidationError
        ElectricityConsumer(
            id=uuid4(),
            path_id=PathID("Test"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
            energy_usage_model=TemporalModel(
                {
                    Period(datetime(1900, 1, 1)): direct_expression_model_factory(
                        expression=Expression.setup_from_expression(value=5), energy_usage_type=EnergyUsageType.POWER
                    )
                }
            ),
            regularity=Regularity(
                expression_evaluator=expression_evaluator,
                expression_input={Period(datetime(1900, 1, 1)): 1},
                target_period=expression_evaluator.get_period(),
            ),
            expression_evaluator=expression_evaluator,
        )
