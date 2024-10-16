from __future__ import annotations

import abc
from datetime import datetime, timedelta
from typing import Dict, List, Protocol, Union

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, assert_never

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.expression.expression import Expression


class VariablesMap(BaseModel):
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

    model_config = ConfigDict(extra="forbid")

    time_vector: List[datetime] = Field(default_factory=list)
    variables: Dict[str, List[Annotated[float, Field(allow_inf_nan=False)]]] = Field(default_factory=dict)

    @property
    def period(self):
        return Period(
            start=self.time_vector[0],
            end=self.time_vector[-1] + timedelta(microseconds=1),  # Make sure the last timestep is included
            # TODO: Change this? Need to change where stuff depends on this ...
        )

    @property
    def length(self) -> int:
        return len(self.time_vector)

    def get_subset(self, start_index: int = 0, end_index: int = -1) -> VariablesMap:
        subset_time_vector = self.time_vector[start_index:end_index]
        subset_dict = {ref: array[start_index:end_index] for ref, array in self.variables.items()}
        return VariablesMap(variables=subset_dict, time_vector=subset_time_vector)

    def get_subset_from_period(self, period: Period) -> VariablesMap:
        start_index, end_index = period.get_timestep_indices(self.time_vector)
        return self.get_subset(start_index, end_index)

    def get_subset_for_timestep(self, current_timestep: datetime) -> VariablesMap:
        """
        Get variables that are active and in use for the given timestep only
        :param current_timestep:
        :return:
        """
        timestep_index = self.time_vector.index(current_timestep)
        return self.get_subset(timestep_index, timestep_index + 1)

    def zeros(self) -> List[float]:
        return [0.0] * len(self.time_vector)

    def get_time_vector(self):
        return self.time_vector

    def get_period(self):
        return self.period

    def evaluate(self, expression: Union[Expression, Dict[datetime, Expression], TemporalModel]) -> NDArray[np.float64]:
        # Should we only allow Expression and Temporal model?
        if isinstance(expression, Expression):
            return expression.evaluate(variables=self.variables, fill_length=len(self.get_time_vector()))
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
                start_index, end_index = period.get_timestep_indices(self.get_time_vector())
                variables_map_for_this_period = self.get_subset(start_index=start_index, end_index=end_index)
                evaluated_expression = variables_map_for_this_period.evaluate(expression)
                result[start_index:end_index] = evaluated_expression
        return np.asarray(result)


class ExpressionEvaluator(Protocol):
    @abc.abstractmethod
    def get_time_vector(self) -> [List[datetime]]: ...

    @abc.abstractmethod
    def get_period(self) -> Period: ...

    @abc.abstractmethod
    def get_subset(self, start_index: int, end_index: int) -> ExpressionEvaluator: ...

    @abc.abstractmethod
    def evaluate(
        self, expression: Union[Expression, TemporalModel, Dict[datetime, Expression]]
    ) -> NDArray[np.float64]: ...
