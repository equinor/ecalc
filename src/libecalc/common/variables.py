from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Annotated

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import Period, Periods


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

    global_time_vector: List[datetime] = Field(default_factory=list)
    variables: Dict[str, List[Annotated[float, Field(allow_inf_nan=False)]]] = Field(default_factory=dict)

    @field_validator("variables", mode="before")
    def check_length_of_time_vector_vs_variables(cls, v: Dict[str, Any], info: ValidationInfo):
        # time_vector should contain one more item than the number of values in each variable
        # if it is not empty []
        if info.data["global_time_vector"] and any(
            len(v[keys]) != len(info.data["global_time_vector"]) - 1 for keys, values in v.items()
        ):
            raise ProgrammingError(
                "Time series: The number of time steps should be one more than the number of values for each variable."
                "Values are for periods defined by consecutive start and end dates."
                "Most likely a bug, report to eCalc Dev Team."
            )
        return v

    @property
    def time_vector(self) -> List[datetime]:
        return self.global_time_vector[:-1]

    @property
    def period(self):
        """Get the period covered by the time vector
        Returns:
            A period object with the start and end of the time vector

        """
        return Period(
            start=self.global_time_vector[0],
            end=self.global_time_vector[-1],
        )

    @property
    def periods(self):
        """Get the periods covered by the time vector

        Returns:
            A list of periods, each period is defined by two consecutive time steps in the time vector
        """
        return Periods.create_periods(times=self.global_time_vector, include_before=False, include_after=False)

    @property
    def length_of_global_time_vector(self) -> int:
        """Get the length of the time vector"""
        return len(self.global_time_vector)

    @property
    def number_of_periods(self) -> int:
        """Get the number of periods covered by the time vector"""
        return len(self.global_time_vector) - 1

    def get_subset(self, start_index: int = 0, end_index: int = -1) -> VariablesMap:
        subset_time_vector = self.global_time_vector[start_index : end_index + 1]
        subset_dict = {ref: array[start_index:end_index] for ref, array in self.variables.items()}
        return VariablesMap(variables=subset_dict, global_time_vector=subset_time_vector)

    def get_subset_from_period(self, period: Period) -> VariablesMap:
        start_index, end_index = period.get_timestep_indices(self.time_vector)
        return self.get_subset(start_index, end_index)

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
        if period.start < self.period.start:
            period.start = self.period.start
        if period.end > self.period.end:
            period.end = self.period.end

        # Check if the start and end of the period of interest are equal to dates in the global time vector
        if period.start in self.global_time_vector and period.end in self.global_time_vector:
            start_index = self.global_time_vector.index(period.start)
            end_index = self.global_time_vector.index(period.end)
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
        timestep_index = self.time_vector.index(current_timestep)
        return self.get_subset(timestep_index, timestep_index + 1)

    def zeros(self) -> List[float]:
        return [0.0] * len(self.time_vector)

    @property
    def first_period(self) -> Period:
        return self.periods.periods[0]

    @property
    def last_period(self) -> Period:
        return self.periods.periods[-1]
