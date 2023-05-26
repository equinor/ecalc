import operator
from functools import reduce
from typing import Dict, List, Protocol, Union, ValuesView

from libecalc.common.list_utils import transpose
from libecalc.common.utils.rates import TimeSeriesBoolean
from libecalc.core.result.emission import EmissionResult


class HasIsValid(Protocol):
    is_valid: TimeSeriesBoolean


def aggregate_is_valid(components: List[HasIsValid]) -> List[bool]:
    is_valid_arrays = [component.is_valid.values for component in components]
    return [all(is_valid_step) for is_valid_step in transpose(is_valid_arrays)]


class HasEmissions(Protocol):
    emissions: List[EmissionResult]


def aggregate_emissions(
    emissions_lists: Union[List[Dict[str, EmissionResult]], ValuesView],
) -> Dict[str, EmissionResult]:
    """Aggregates emissions e.g. for a total asset across installations
    Args:
        emissions_lists (List[Dict[str, EmissionResult]] or dict.values): Includes emissions to aggregate

    Returns:
        dto.types.FuelType
    """

    all_emissions = [emission for emissions in emissions_lists for emission in emissions.values()]

    # Keep order of emissions
    emission_names = []
    for emission in all_emissions:
        if emission.name not in emission_names:
            emission_names.append(emission.name)

    emissions_aggregated = {}
    for emission_name in emission_names:
        emissions = [emission for emission in all_emissions if emission.name == emission_name]

        emissions_aggregated[emission_name] = EmissionResult(
            name=emission_name,
            timesteps=emissions[0].timesteps,
            rate=reduce(operator.add, [emission.rate for emission in emissions]),
            tax=reduce(operator.add, [emission.tax for emission in emissions]),
            quota=reduce(operator.add, [emission.quota for emission in emissions]),
        )

    return emissions_aggregated
