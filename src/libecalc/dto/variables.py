from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

from libecalc.common.time_utils import Period


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
