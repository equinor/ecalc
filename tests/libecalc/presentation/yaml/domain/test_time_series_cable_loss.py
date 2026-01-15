from datetime import datetime

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.consumer_category import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.domain.expression_time_series_cable_loss import ExpressionTimeSeriesCableLoss
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

periods = [
    Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1)),
    Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1)),
    Period(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1)),
]


def test_single_category_power_from_shore(expression_evaluator_factory):
    """Cable loss is used for all periods when category is POWER_FROM_SHORE."""
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;CABLE_LOSS": [0.1, 0.2, 0.3]}
    )
    cable_loss_expr = TimeSeriesExpression(expression="SIM1;CABLE_LOSS", expression_evaluator=evaluator)
    cable_loss = ExpressionTimeSeriesCableLoss(
        time_series_expression=cable_loss_expr,
        category=TemporalModel.create(
            ConsumerUserDefinedCategoryType.POWER_FROM_SHORE, target_period=evaluator.get_period()
        ),
    )
    assert cable_loss.get_values() == [0.1, 0.2, 0.3]


def test_single_category_other(expression_evaluator_factory):
    """Cable loss is zero for all periods when category is not POWER_FROM_SHORE."""
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;CABLE_LOSS": [0.1, 0.2, 0.3]}
    )
    cable_loss_expr = TimeSeriesExpression(expression="SIM1;CABLE_LOSS", expression_evaluator=evaluator)
    cable_loss = ExpressionTimeSeriesCableLoss(
        time_series_expression=cable_loss_expr,
        category=TemporalModel.create(
            ConsumerUserDefinedCategoryType.TURBINE_GENERATOR, target_period=evaluator.get_period()
        ),
    )
    assert cable_loss.get_values() == [0.0, 0.0, 0.0]


def test_temporal_category_switch(expression_evaluator_factory):
    """
    Cable loss is set to zero for periods before switching to POWER_FROM_SHORE,
    and applied for periods after the switch.
    """

    category_model = {
        periods[0].start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        periods[1].start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
    }
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;CABLE_LOSS": [0.1, 0.2, 0.3]}
    )
    cable_loss_expr = TimeSeriesExpression(expression="SIM1;CABLE_LOSS", expression_evaluator=evaluator)
    cable_loss = ExpressionTimeSeriesCableLoss(
        time_series_expression=cable_loss_expr,
        category=TemporalModel.create(category_model, target_period=evaluator.get_period()),
    )
    assert cable_loss.get_values() == [0.0, 0.2, 0.3]


def test_temporal_category_switch_back(expression_evaluator_factory):
    """
    Cable loss is applied for periods before switching away from POWER_FROM_SHORE,
    and set to zero for periods after the switch.
    """

    category_model = {
        periods[0].start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
        periods[1].start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
    }
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;CABLE_LOSS": [0.1, 0.2, 0.3]}
    )
    cable_loss_expr = TimeSeriesExpression(expression="SIM1;CABLE_LOSS", expression_evaluator=evaluator)
    cable_loss = ExpressionTimeSeriesCableLoss(
        time_series_expression=cable_loss_expr,
        category=TemporalModel.create(category_model, target_period=evaluator.get_period()),
    )
    assert cable_loss.get_values() == [0.1, 0.0, 0.0]
