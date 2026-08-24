from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.time_utils import Period, Periods
from libecalc.common.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.strict_expression_evaluator import StrictExpressionEvaluator
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable


def _make_time_series_resource(time_vector: list[datetime], columns: dict[str, list[float]]) -> TimeSeriesResource:
    """Create a TimeSeriesResource from a time vector and column data."""
    resource = MagicMock()
    headers = ["DATE"] + list(columns.keys())
    # TimeSeriesResource expects date strings, not datetime objects
    date_strings = [dt.strftime("%Y-%m-%d") for dt in time_vector]
    resource.get_headers.return_value = headers
    resource.get_column.side_effect = lambda h: date_strings if h == "DATE" else columns[h]
    return TimeSeriesResource(resource)


def _make_variables_map(time_vector: list[datetime], variables: dict[str, list[float]] | None = None) -> VariablesMap:
    periods = Periods.create_periods(time_vector, include_before=False, include_after=False)
    return VariablesMap(periods=periods, variables=variables or {})


class TestStrictExpressionEvaluatorInit:
    def test_delegates_to_variables_map(self):
        time_vector = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        variables = {"SIM;col1": [1.0, 2.0]}
        vm = _make_variables_map(time_vector, variables)
        evaluator = StrictExpressionEvaluator(variables_map=vm)

        assert evaluator.get_time_vector() == time_vector
        assert evaluator.get_periods() == vm.get_periods()
        assert evaluator.get_period() == vm.get_period()

    def test_evaluate_delegates(self):
        time_vector = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        variables = {"SIM;col1": [10.0, 20.0]}
        vm = _make_variables_map(time_vector, variables)
        evaluator = StrictExpressionEvaluator(variables_map=vm)

        expr = Expression.setup_from_expression(value=10)
        result = evaluator.evaluate(expr)
        np.testing.assert_array_equal(result, vm.evaluate(expr))

    def test_get_subset(self):
        time_vector = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        vm = _make_variables_map(time_vector)
        evaluator = StrictExpressionEvaluator(variables_map=vm)
        subset = evaluator.get_subset(0, 1)
        assert subset is not None

    def test_get_subset_for_period(self):
        time_vector = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        vm = _make_variables_map(time_vector)
        evaluator = StrictExpressionEvaluator(variables_map=vm)
        period = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
        subset = evaluator.get_subset_for_period(period)
        assert subset is not None


class TestFromExpressionReferences:
    """Tests for the from_expression_references class method."""

    def _make_tsr(self, time_vector: list[datetime], columns: dict[str, list[float]]) -> TimeSeriesResource:
        return _make_time_series_resource(time_vector, columns)

    def test_single_time_series_reference(self):
        tv = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        tsr = self._make_tsr(tv, {"col1": [10.0, 20.0, 30.0]})

        evaluator = StrictExpressionEvaluator.from_expression_references(
            expression_references={"SIM;col1"},
            variables={},
            time_series_resources={"SIM": tsr},
            start=datetime(2020, 1, 1),
            end=datetime(2022, 1, 1),
        )

        assert evaluator.get_time_vector() == tv

    def test_no_time_series_with_start(self):
        """When no time series references exist, use start as the only timestep."""
        evaluator = StrictExpressionEvaluator.from_expression_references(
            expression_references=set(),
            variables={},
            time_series_resources={},
            start=datetime(2020, 1, 1),
            end=datetime(2022, 1, 1),
        )

        assert evaluator.get_time_vector() == [datetime(2020, 1, 1), datetime(2022, 1, 1)]

    def test_no_time_series_no_start_raises(self):
        """When no time series references and no start, should raise."""
        with pytest.raises(EcalcError, match="No time steps"):
            StrictExpressionEvaluator.from_expression_references(
                expression_references=set(),
                variables={},
                time_series_resources={},
                start=None,
                end=datetime(2022, 1, 1),
            )

    def test_mismatching_time_vectors_raises(self):
        tv1 = [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        tv2 = [datetime(2020, 1, 1), datetime(2021, 6, 1)]
        tsr1 = self._make_tsr(tv1, {"col1": [1.0, 2.0]})
        tsr2 = self._make_tsr(tv2, {"col2": [3.0, 4.0]})

        with pytest.raises(EcalcError, match="Mismatching timesteps"):
            StrictExpressionEvaluator.from_expression_references(
                expression_references={"SIM1;col1", "SIM2;col2"},
                variables={},
                time_series_resources={"SIM1": tsr1, "SIM2": tsr2},
                start=datetime(2020, 1, 1),
                end=datetime(2021, 1, 1),
            )

    def test_start_not_in_time_vector_raises(self):
        tv = [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        tsr = self._make_tsr(tv, {"col1": [1.0, 2.0]})

        with pytest.raises(EcalcError, match="start should exist"):
            StrictExpressionEvaluator.from_expression_references(
                expression_references={"SIM;col1"},
                variables={},
                time_series_resources={"SIM": tsr},
                start=datetime(2019, 6, 1),
                end=datetime(2021, 1, 1),
            )

    def test_start_none_uses_full_time_vector(self):
        tv = [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        tsr = self._make_tsr(tv, {"col1": [1.0, 2.0]})

        evaluator = StrictExpressionEvaluator.from_expression_references(
            expression_references={"SIM;col1"},
            variables={},
            time_series_resources={"SIM": tsr},
            start=None,
            end=datetime(2022, 1, 1),
        )

        # time_vector should be [2020, 2021, 2022(end)]
        assert evaluator.get_time_vector() == [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]

    def test_filters_time_vector_by_start_end(self):
        tv = [datetime(2019, 1, 1), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        tsr = self._make_tsr(tv, {"col1": [1.0, 2.0, 3.0, 4.0]})

        evaluator = StrictExpressionEvaluator.from_expression_references(
            expression_references={"SIM;col1"},
            variables={},
            time_series_resources={"SIM": tsr},
            start=datetime(2020, 1, 1),
            end=datetime(2022, 1, 1),
        )

        # Should include 2020, 2021 (within [start, end)), plus end appended
        assert evaluator.get_time_vector() == [
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
        ]

    def test_with_variable_references(self):
        """Test that $var.* references are resolved transitively."""
        tv = [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        tsr = self._make_tsr(tv, {"col1": [10.0, 20.0]})

        variables = {
            "my_var": YamlSingleVariable(value=Expression.setup_from_expression("SIM;col1 {+} 1")),
        }

        evaluator = StrictExpressionEvaluator.from_expression_references(
            expression_references={"$var.my_var"},
            variables=variables,
            time_series_resources={"SIM": tsr},
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
        )

        assert evaluator.get_time_vector() == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
