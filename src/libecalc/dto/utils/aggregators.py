import operator
from functools import reduce
from typing import Dict, List, Protocol

from libecalc.common.list.list_utils import transpose
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
)
from libecalc.dto.result.emission import PartialEmissionResult


class HasIsValid(Protocol):
    is_valid: TimeSeriesBoolean


def aggregate_is_valid(components: List[HasIsValid]) -> List[bool]:
    is_valid_arrays = [component.is_valid.values for component in components]
    return [all(is_valid_step) for is_valid_step in transpose(is_valid_arrays)]


class HasEmissions(Protocol):
    emissions: List[PartialEmissionResult]


def aggregate_emissions(
    emissions_lists: List[Dict[str, PartialEmissionResult]],
) -> Dict[str, PartialEmissionResult]:
    """Aggregates emissions e.g. for a total asset across installations
    Args:
        emissions_lists (List[Dict[str, PartialEmissionResult]] or dict.values): Includes emissions to aggregate

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

        emissions_aggregated[emission_name] = PartialEmissionResult(
            name=emission_name,
            timesteps=emissions[0].timesteps,
            rate=reduce(operator.add, [emission.rate.to_calendar_day() for emission in emissions]),
        )

    return emissions_aggregated
