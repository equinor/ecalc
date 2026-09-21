from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import FuelGasRate
from libecalc.presentation.yaml.domain.energy.consumers import TimeSeriesFuelGasConsumer, expression_demand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

period = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))


def test_consumer_get_demand_delegates_to_its_demand_function():
    """TimeSeriesConsumer.get_demand is just a thin call to whatever demand function it
    was built with - it has no energy-type or expression knowledge of its own. A fake demand
    function is used here so this test does not depend on expression_demand's own correctness,
    which is covered separately below. TimeSeriesFuelGasConsumer is used only because
    TimeSeriesConsumer itself is abstract; its concrete get_input_energy_type is irrelevant here."""
    consumer = TimeSeriesFuelGasConsumer(name="consumer", demand=lambda p: FuelGasRate(42) if p == period else None)

    assert consumer.get_demand(period) == FuelGasRate(42)


def test_expression_demand_evaluates_expression_and_wraps_it_in_energy_type(expression_evaluator_factory):
    evaluator = expression_evaluator_factory.from_periods(periods=[period])
    demand = expression_demand(TimeSeriesExpression(expression=50, expression_evaluator=evaluator), FuelGasRate)

    result = demand(period)

    assert type(result) is FuelGasRate
    assert result.value == 50


def test_expression_demand_is_none_without_an_expression():
    """A consumer with no demand expression at all (e.g. not applicable for the current
    configuration) should report no demand, rather than raising or defaulting to zero."""
    demand = expression_demand(None, FuelGasRate)

    assert demand(period) is None
