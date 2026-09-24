from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import ElectricalPower
from libecalc.presentation.yaml.domain.energy.consumers import TimeSeriesConsumer
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TestTimeSeriesConsumer:
    def test_demand_for_forwards_the_requested_period_to_the_demand_callable(self):
        period_a = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
        period_b = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
        values_by_period = {period_a: ElectricalPower(1), period_b: ElectricalPower(2)}
        consumer = TimeSeriesConsumer(name="load", demand_for=lambda p: values_by_period[p])

        assert consumer.get_demand(period_a) == ElectricalPower(1)
        assert consumer.get_demand(period_b) == ElectricalPower(2)


class TestFromExpression:
    def test_evaluates_expression_per_period(self, expression_evaluator_factory):
        period_a = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
        period_b = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
        expression_evaluator = expression_evaluator_factory.from_periods(
            periods=[period_a, period_b],
            variables={"TSA;RATE": [5, 9]},
        )
        expression = TimeSeriesExpression(expression="TSA;RATE", expression_evaluator=expression_evaluator)
        consumer = TimeSeriesConsumer.from_expression(name="load", expression=expression, energy_type=ElectricalPower)

        assert consumer.get_demand(period_a) == ElectricalPower(5)
        assert consumer.get_demand(period_b) == ElectricalPower(9)

    def test_returns_none_when_expression_is_none(self, period):
        consumer = TimeSeriesConsumer.from_expression(name="load", expression=None, energy_type=ElectricalPower)
        assert consumer.get_demand(period) is None


class TestFromProcessSimulation:
    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            TimeSeriesConsumer.from_process_simulation(name="load", energy_type=ElectricalPower)
