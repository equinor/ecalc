import numpy as np

from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.fuel_type import FuelType


class FuelModel:
    """A function to evaluate fuel related attributes for different time period
    For each period, there is a data object with expressions for fuel related
    attributes which may be evaluated for some variables and a fuel_rate.
    """

    def __init__(self, fuel_time_function_dict: TemporalModel[FuelType], expression_evaluator: ExpressionEvaluator):
        logger.debug("Creating fuel model")
        self.temporal_fuel_model = fuel_time_function_dict
        self._expression_evaluator = expression_evaluator

    def evaluate_emissions(self, fuel_rate: list[float]) -> dict[str, TimeSeriesStreamDayRate]:
        """Evaluate fuel related expressions and results for a TimeSeriesCollection and a
        fuel_rate array.

        First the fuel parameters are calculated by evaluating the fuel expressions and
        the time_series object.

        Then the resulting emission volume is calculated based on the fuel rate:
        - emission_rate = emission_factor * fuel_rate

        This is done per time period and all fuel related results both in terms of
        fuel types and time periods, are merged into one common fuel collection results object.

        The length of the fuel_rate array must equal the length of the global list of periods.
        It is assumed that the fuel_rate array origins from calculations based on the same time_series
        object and thus will have the same length when used in this method.
        """
        logger.debug("Evaluating fuel usage and emissions")

        fuel_rate = np.asarray(fuel_rate)

        all_periods = self._expression_evaluator.get_periods()

        # Creating a pseudo-default dict with all the emitters as keys. This is to handle changes in a temporal model.
        emissions = {
            emission_name: TimeSeriesStreamDayRate(
                periods=all_periods, values=[0.0] * len(all_periods), unit=Unit.TONS_PER_DAY
            )
            for emission_name in {
                emission.name for _, model in self.temporal_fuel_model.items() for emission in model.emissions
            }
        }

        for temporal_period, model in self.temporal_fuel_model.items():
            if Period.intersects(temporal_period, self._expression_evaluator.get_period()):
                start_index, end_index = temporal_period.get_period_indices(self._expression_evaluator.get_periods())
                variables_map_this_period = self._expression_evaluator.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                fuel_rate_this_period = fuel_rate[start_index:end_index]
                for emission in model.emissions:
                    factor = variables_map_this_period.evaluate(expression=emission.factor)

                    emission_rate_kg_per_day = fuel_rate_this_period * factor
                    emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(
                        emission_rate_kg_per_day
                    ).tolist()

                    for i in range(len(emission_rate_tons_per_day)):
                        assert emissions[emission.name].values[i + start_index] == 0.0, (
                            "Only one fuel model should affect a period"
                        )
                        emissions[emission.name].values[i + start_index] += emission_rate_tons_per_day[i]

        return dict(sorted(emissions.items()))
