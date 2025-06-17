from __future__ import annotations

import abc
from datetime import datetime
from typing import Protocol, assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.expression.expression import Expression


class VariablesMap:
    """A map of all (timeseries) variables that can be used in eCalc YAML
    A variable name has the format "{name_of_case};{title_of_header} from the original
    file/resource with time series, ie;

    A file is named "reservoir1" and contains headers "rgi" and "pwi", then this will
    result in 2 mappings in this object; "reservoir1;rgi" and "reservoir1;pwi", which
    can be referred to in the eCalc YAML.

    Currently, the relevant variables are sent/injected to the components that have used
    it in the yaml, but at some point it may be replaced with the data/parameters directly,
    ie the variables will be evaluated before the calculation starts.

    The variables must be interpolated and extrapolated before being added to the variablesmap,
    to make sure that the resolution of ALL variables are the same for everywhere it is being used,
    BEFORE the calculation starts; ie happens as a pre step before calculation, and not in the calculation
    directly.
    """

    def __init__(self, periods: Periods, variables: dict[str, list[float]] = None):
        self._periods = periods
        self._time_vector = periods.all_dates
        self._variables = variables or {}

    @property
    def variables(self) -> dict[str, list[float]]:
        return self._variables

    @property
    def period(self):
        return Period(
            start=self._time_vector[0],
            end=self._time_vector[-1],
        )

    @property
    def length(self) -> int:
        return len(self._time_vector)

    def get_subset(self, start_index: int = 0, end_index: int = -1) -> VariablesMap:
        subset_time_vector = self._time_vector[start_index : end_index + 1]
        subset_dict = {ref: array[start_index:end_index] for ref, array in self._variables.items()}
        return VariablesMap(
            variables=subset_dict,
            periods=Periods.create_periods(subset_time_vector, include_before=False, include_after=False),
        )

    def get_subset_for_period(self, period: Period) -> VariablesMap:
        """Get variables that are active and in use for the given period only
        Args:
            period: The period for which the variables are needed
        Returns:
            A VariablesMap object with the variables for the given period
        """
        # Check if the given period intersects with the global period
        if not Period.intersects(self.period, period):
            return self.get_subset(0, 0)

        # Adjust the period to the global period if needed
        period_start = max(period.start, self.period.start)
        period_end = min(period.end, self.period.end)

        # Check if the start and end of the period of interest are equal to dates in the global time vector
        if period_start in self._time_vector and period_end in self._time_vector:
            start_index = self._time_vector.index(period.start)
            end_index = self._time_vector.index(period.end)
        else:
            raise ProgrammingError(
                "Trying to access a period that does not exist in the global time vector. Please contact eCalc support."
            )
        return self.get_subset(start_index, end_index)

    def get_subset_for_timestep(self, current_timestep: datetime) -> VariablesMap:
        """
        Get variables that are active and in use for the given timestep only
        :param current_timestep:
        :return:
        """
        timestep_index = self._time_vector.index(current_timestep)
        return self.get_subset(timestep_index, timestep_index + 1)

    def zeros(self) -> list[float]:
        return [0.0] * len(self.periods)

    def get_time_vector(self):
        return self._time_vector

    def get_periods(self):
        return self.periods

    def get_period(self):
        return self.period

    @property
    def periods(self):
        """Get the periods covered by the time vector
        Returns:
            A list of periods, each period is defined by two consecutive time steps in the time vector
        """
        return self._periods

    @property
    def number_of_periods(self) -> int:
        """Get the number of periods covered by the time vector"""
        return len(self._time_vector) - 1

    def evaluate(
        self, expression: Expression | dict[Period, Expression] | TemporalModel[Expression]
    ) -> NDArray[np.float64]:
        # Should we only allow Expression and Temporal model?
        if isinstance(expression, Expression):
            return expression.evaluate(variables=self._variables, fill_length=len(self.get_periods()))
        elif isinstance(expression, dict):
            return self._evaluate_temporal(temporal_expression=TemporalModel(expression))
        elif isinstance(expression, TemporalModel):
            return self._evaluate_temporal(temporal_expression=expression)

        assert_never(expression)

    def _evaluate_temporal(
        self,
        temporal_expression: TemporalModel[Expression],
    ) -> NDArray[np.float64]:
        result = self.zeros()

        for period, expression in temporal_expression.items():
            if Period.intersects(period, self.get_period()):
                start_index, end_index = period.get_period_indices(self.get_periods())
                variables_map_for_this_period = self.get_subset(start_index=start_index, end_index=end_index)
                evaluated_expression = variables_map_for_this_period.evaluate(expression)
                result[start_index:end_index] = evaluated_expression
        return np.asarray(result)


class ExpressionEvaluator(Protocol):
    @abc.abstractmethod
    def get_time_vector(self) -> list[datetime]: ...

    @abc.abstractmethod
    def get_period(self) -> Period: ...

    @abc.abstractmethod
    def get_periods(self) -> Periods: ...

    @abc.abstractmethod
    def get_subset(self, start_index: int, end_index: int) -> ExpressionEvaluator: ...

    @abc.abstractmethod
    def get_subset_for_period(self, period: Period) -> ExpressionEvaluator: ...

    @abc.abstractmethod
    def evaluate(self, expression: Expression | TemporalModel | dict[Period, Expression]) -> NDArray[np.float64]: ...
