from datetime import datetime
from typing import List

import numpy as np
from numpy.typing import NDArray

from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    TimeSeriesBoolean,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import GeneratorSetResult


class Genset:
    def __init__(
        self,
        id: str,
        name: str,
        temporal_generator_set_model: TemporalModel[GeneratorModelSampled],
    ):
        logger.debug(f"Creating Genset: {name}")
        self.id = id
        self.name = name
        self.temporal_generator_set_model = temporal_generator_set_model

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        power_requirement: NDArray[np.float64],
    ) -> GeneratorSetResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid timesteps. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating Genset: {self.name}")

        if not len(power_requirement) == len(expression_evaluator.get_time_vector()):
            raise ValueError("length of power_requirement does not match the time vector.")

        # Compute fuel consumption from power rate.
        fuel_rate = self.evaluate_fuel_rate(
            power_requirement,
            time_vector=expression_evaluator.get_time_vector(),
            actual_period=expression_evaluator.get_period(),
        )
        power_capacity_margin = self.evaluate_power_capacity_margin(
            power_requirement,
            time_vector=expression_evaluator.get_time_vector(),
            actual_period=expression_evaluator.get_period(),
        )

        # Convert fuel_rate to calendar day rate
        # fuel_rate = Rates.to_calendar_day(stream_day_rates=fuel_rate, regularity=regularity)
        # TODO: Ok to not convert to calendar day here? Seems that all legacy stuff needs to be dealt with anyways...

        # Check for extrapolations (in el-to-fuel, powers are checked in consumers)
        valid_timesteps = np.logical_and(~np.isnan(fuel_rate), power_capacity_margin >= 0)

        extrapolations = np.isnan(fuel_rate)  # noqa
        fuel_rate = Rates.forward_fill_nan_values(rates=fuel_rate)

        # By convention, we change remaining NaN-values to 0 regardless of extrapolation
        fuel_rate = np.nan_to_num(fuel_rate)

        return GeneratorSetResult(
            id=self.id,
            timesteps=expression_evaluator.get_time_vector(),
            is_valid=TimeSeriesBoolean(
                timesteps=expression_evaluator.get_time_vector(),
                values=array_to_list(valid_timesteps),
                unit=Unit.NONE,
            ),
            power_capacity_margin=TimeSeriesStreamDayRate(
                timesteps=expression_evaluator.get_time_vector(),
                values=array_to_list(power_capacity_margin),
                unit=Unit.MEGA_WATT,
            ),
            power=TimeSeriesStreamDayRate(
                timesteps=expression_evaluator.get_time_vector(),
                values=array_to_list(power_requirement),
                unit=Unit.MEGA_WATT,
            ),
            energy_usage=TimeSeriesStreamDayRate(
                timesteps=expression_evaluator.get_time_vector(),
                values=array_to_list(fuel_rate),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
        )

    def evaluate_fuel_rate(
        self,
        power_requirement: NDArray[np.float64],
        time_vector: [List[datetime]],
        actual_period: Period,
    ) -> NDArray[np.float64]:
        result = np.full_like(power_requirement, fill_value=np.nan).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                start_index, end_index = period.get_timestep_indices(time_vector)
                result[start_index:end_index] = model.evaluate(power_requirement[start_index:end_index])
        return result

    def evaluate_power_capacity_margin(
        self,
        power_requirement: NDArray[np.float64],
        time_vector: [List[datetime]],
        actual_period: Period,
    ) -> NDArray[np.float64]:
        result = np.zeros_like(power_requirement).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                start_index, end_index = period.get_timestep_indices(time_vector)
                result[start_index:end_index] = model.evaluate_power_capacity_margin(
                    power_requirement[start_index:end_index]
                )
        return result
