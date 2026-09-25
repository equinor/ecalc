from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import ElectricalPower
from libecalc.presentation.yaml.domain.energy.consumers import TimeSeriesConsumer
from libecalc.presentation.yaml.domain.energy.demand import ExpressionDemand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TestTimeSeriesConsumer:
    def test_get_demand_delegates_to_the_demand(self, expression_evaluator_factory, period):
        expression_evaluator = expression_evaluator_factory.from_periods(
            periods=[period],
            variables={"TSA;RATE": [5]},
        )
        expression = TimeSeriesExpression(expression="TSA;RATE", expression_evaluator=expression_evaluator)
        consumer = TimeSeriesConsumer(
            name="load", demand=ExpressionDemand(energy_type=ElectricalPower, expression=expression)
        )

        assert consumer.get_demand(period) == ElectricalPower(5)

    def test_get_input_energy_type_delegates_to_the_demand(self):
        consumer = TimeSeriesConsumer(
            name="load", demand=ExpressionDemand(energy_type=ElectricalPower, expression=None)
        )

        assert consumer.get_input_energy_type() is ElectricalPower


class TestExpressionDemand:
    def test_evaluates_expression_per_period(self, expression_evaluator_factory):
        period_a = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
        period_b = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
        expression_evaluator = expression_evaluator_factory.from_periods(
            periods=[period_a, period_b],
            variables={"TSA;RATE": [5, 9]},
        )
        expression = TimeSeriesExpression(expression="TSA;RATE", expression_evaluator=expression_evaluator)
        demand = ExpressionDemand(energy_type=ElectricalPower, expression=expression)

        assert demand.get_demand(period_a) == ElectricalPower(5)
        assert demand.get_demand(period_b) == ElectricalPower(9)

    def test_returns_none_when_expression_is_none(self, period):
        demand = ExpressionDemand(energy_type=ElectricalPower, expression=None)

        assert demand.get_demand(period) is None
