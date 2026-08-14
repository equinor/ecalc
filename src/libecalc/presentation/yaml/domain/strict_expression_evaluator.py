from collections import defaultdict
from datetime import datetime
from typing import Self

import numpy as np
from numpy._typing import NDArray

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.domain.variables_graph import VariablesGraph
from libecalc.presentation.yaml.mappers.variables_mapper.variables_mapper import evaluate_variables
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables


class StrictExpressionEvaluator(ExpressionEvaluator):
    def __init__(self, variables_map: VariablesMap):
        self._variables_map = variables_map

    @classmethod
    def from_expression_references(
        cls,
        expression_references: set[str],
        variables: YamlVariables,
        time_series_resources: dict[
            str, TimeSeriesResource
        ],  # str is time series name, should match reference in expressions.
        start: datetime | None,
        end: datetime,
    ) -> Self:

        # Resolve $var.* references transitively to discover indirect time series dependencies
        var_names = {ref.removeprefix("$var.") for ref in expression_references if ref.startswith("$var.")}
        if var_names:
            graph = VariablesGraph(variables)
            var_refs = graph.get_references(var_names)
            all_refs = expression_references.union(var_refs)
        else:
            all_refs = expression_references

        ts_references = [ref for ref in all_refs if ";" in ref]
        expression_references_map: dict[str, list[str]] = defaultdict(list)
        for ts_reference in ts_references:
            time_series_resource_name, time_series_column_name = ts_reference.split(";")
            expression_references_map[time_series_resource_name].append(time_series_column_name)

        time_series_resources_used = {
            tsr_name: tsr for tsr_name, tsr in time_series_resources.items() if tsr_name in expression_references_map
        }

        # Validate matching time vectors for all time series resources used in the expression references
        if len(time_series_resources_used) > 0:
            first_tsr_name = list(time_series_resources_used)[0]
            first_tsr_time_vector = time_series_resources_used[first_tsr_name].get_time_vector()
            for tsr_name, tsr in time_series_resources_used.items():
                if tsr.get_time_vector() != first_tsr_time_vector:
                    raise EcalcError(
                        title="Mismatching timesteps",
                        message=f"Time series {tsr_name} has a different time vector than the first time series {first_tsr_name}.",
                    )
            if start is not None:
                if start not in first_tsr_time_vector:
                    raise EcalcError(
                        title="Invalid time series", message="The specified start should exist in the time series"
                    )
                time_vector = [time for time in first_tsr_time_vector if start <= time < end]
            else:
                time_vector = [time for time in first_tsr_time_vector if time < end]
        else:
            if start is None:
                raise EcalcError(title="Invalid time series", message="No time steps to calculate")
            time_vector = [start]

        time_vector = [*time_vector, end]  # Start already included and confirmed to exist in time series resources
        periods = Periods.create_periods(time_vector, include_before=False, include_after=False)

        time_series_columns: dict[str, list[float]] = {}
        for tsr_name in expression_references_map:
            tsr = time_series_resources_used[tsr_name]
            for tsr_column in expression_references_map[tsr_name]:
                time_series_columns[f"{tsr_name};{tsr_column}"] = tsr.get_float_column(tsr_column)

        referenced_variables = {}
        for ref in all_refs:
            if ref.startswith("$var."):
                var_name = ref.removeprefix("$var.")
                referenced_variables[var_name] = variables[var_name]

        processed_variables = evaluate_variables(
            variables=referenced_variables, processed_variables=time_series_columns, periods=periods
        )
        return cls(variables_map=processed_variables)

    def get_time_vector(self) -> list[datetime]:
        return self._variables_map.get_time_vector()

    def get_period(self) -> Period:
        return self._variables_map.get_period()

    def get_periods(self) -> Periods:
        return self._variables_map.get_periods()

    def get_subset(self, start_index: int, end_index: int) -> ExpressionEvaluator:
        return self._variables_map.get_subset(start_index, end_index)

    def get_subset_for_period(self, period: Period) -> ExpressionEvaluator:
        return self._variables_map.get_subset_for_period(period)

    def evaluate(self, expression: Expression | TemporalModel | dict[Period, Expression]) -> NDArray[np.float64]:
        return self._variables_map.evaluate(expression)
