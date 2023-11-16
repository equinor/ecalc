from datetime import datetime
from typing import Dict

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result.emission import EmissionResult


class FuelModel:
    """A function to evaluate fuel related attributes for different time intervals
    For each time interval, there is a data object with expressions for fuel related
    attributes which may be evaluated for some variables and a fuel_rate.
    """

    def __init__(self, fuel_time_function_dict: Dict[datetime, dto.FuelType]):
        logger.debug("Creating fuel model")
        self.temporal_fuel_model = TemporalModel(fuel_time_function_dict)

    def evaluate_emissions(
        self, variables_map: dto.VariablesMap, fuel_rate: NDArray[np.float64]
    ) -> Dict[str, EmissionResult]:
        """Evaluate fuel related expressions and results for a TimeSeriesCollection and a
        fuel_rate array.

        First the fuel parameters are calculated by evaluating the fuel expressions and
        the time_series object.

        Then the resulting emission volume is calculated based on the fuel rate:
        - emission_rate = emission_factor * fuel_rate

        This is done per time interval and all fuel related results both in terms of
        fuel types and time intervals, are merged into one common fuel collection results object.

        The length of the fuel_rate array must equal the length of the time_vector
        array for the time_series. It is assumed that the fuel_rate array origins
        from calculations based on the same time_series object and thus will have
        the same length when used in this method.
        """
        logger.debug("Evaluating fuel usage and emissions")

        # Creating a pseudo-default dict with all the emitters as keys. This is to handle changes in a temporal model.
        emissions = {
            emission_name: EmissionResult.create_empty(name=emission_name, timesteps=[])
            for emission_name in {
                emission.name for _, model in self.temporal_fuel_model.items() for emission in model.emissions
            }
        }

        for period, model in self.temporal_fuel_model.items():
            if Period.intersects(period, variables_map.period):
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                variables_map_this_period = variables_map.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                fuel_rate_this_period = fuel_rate[start_index:end_index]
                for emission in model.emissions:
                    factor = emission.factor.evaluate(
                        variables=variables_map_this_period.variables,
                        fill_length=len(variables_map_this_period.time_vector),
                    )

                    emission_rate_kg_per_day = fuel_rate_this_period * factor
                    emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate_kg_per_day)

                    result = EmissionResult(
                        name=emission.name,
                        timesteps=variables_map_this_period.time_vector,
                        rate=TimeSeriesStreamDayRate(
                            timesteps=variables_map_this_period.time_vector,
                            values=emission_rate_tons_per_day.tolist(),
                            unit=Unit.TONS_PER_DAY,
                        ),
                    )

                    emissions[emission.name].extend(result)

                for name in emissions:
                    if name not in [emission.name for emission in model.emissions]:
                        emissions[name].extend(
                            EmissionResult.create_empty(name=name, timesteps=variables_map_this_period.time_vector)
                        )

        return dict(sorted(emissions.items()))
