from datetime import datetime

import pytest

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.domain.regularity import Regularity
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import InvalidFlowRateException


def test_negative_fuel_rate_direct_fuel_consumer(expression_evaluator_factory, direct_expression_model_factory):
    period1 = Period(datetime(2027, 1, 1), datetime(2028, 1, 1))
    period2 = Period(datetime(2028, 1, 1), datetime(2029, 1, 1))
    periods = Periods([period1, period2])
    expression_evaluator = expression_evaluator_factory.from_periods_obj(periods=periods)

    negative_fuel = -1
    positive_fuel = 1
    regularity = Regularity(expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period())
    with pytest.raises(InvalidFlowRateException):
        TemporalModel(
            {
                period: direct_expression_model_factory(
                    expression=expr,
                    energy_usage_type=EnergyUsageType.FUEL,
                    expression_evaluator=expression_evaluator.get_subset(
                        *period.get_period_indices(expression_evaluator.get_periods())
                    ),
                    regularity=regularity.get_subset(*period.get_period_indices(expression_evaluator.get_periods())),
                )
                for period, expr in zip([period1, period2], [negative_fuel, positive_fuel])
            }
        )
