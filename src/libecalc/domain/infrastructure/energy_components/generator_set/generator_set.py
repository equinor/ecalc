import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import GeneratorSetResult
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.process.core.generator import GeneratorModelSampled


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
        power_requirement: TimeSeriesFloat | None,
    ) -> GeneratorSetResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid periods. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating Genset: {self.name}")

        if power_requirement is None:
            raise EcalcError(title="Invalid generator set", message="No consumption for generator set")

        assert power_requirement.unit == Unit.MEGA_WATT

        if not len(power_requirement) == len(expression_evaluator.get_periods()):
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.name,
                        message="length of power_requirement does not match the time vector.",
                    )
                ]
            )

        # Compute fuel consumption from power rate.
        fuel_rate = self.evaluate_fuel_rate(
            power_requirement,
            periods=expression_evaluator.get_periods(),
            actual_period=expression_evaluator.get_period(),
        )
        power_capacity_margin = self.evaluate_power_capacity_margin(
            power_requirement,
            periods=expression_evaluator.get_periods(),
            actual_period=expression_evaluator.get_period(),
        )

        # Check for extrapolations (in el-to-fuel, powers are checked in consumers)
        valid_periods = np.logical_and(~np.isnan(fuel_rate), power_capacity_margin >= 0)

        extrapolations = np.isnan(fuel_rate)  # noqa
        fuel_rate = Rates.forward_fill_nan_values(rates=fuel_rate)

        # By convention, we change remaining NaN-values to 0 regardless of extrapolation
        fuel_rate = np.nan_to_num(fuel_rate)

        return GeneratorSetResult(
            id=self.id,
            periods=expression_evaluator.get_periods(),
            is_valid=TimeSeriesBoolean(
                periods=expression_evaluator.get_periods(),
                values=array_to_list(valid_periods),
                unit=Unit.NONE,
            ),
            power_capacity_margin=TimeSeriesStreamDayRate(
                periods=expression_evaluator.get_periods(),
                values=array_to_list(power_capacity_margin),
                unit=Unit.MEGA_WATT,
            ),
            power=TimeSeriesStreamDayRate(
                periods=expression_evaluator.get_periods(),
                values=power_requirement.values,
                unit=Unit.MEGA_WATT,
            ),
            energy_usage=TimeSeriesStreamDayRate(
                periods=expression_evaluator.get_periods(),
                values=array_to_list(fuel_rate),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
        )

    def evaluate_fuel_rate(
        self,
        power_requirement: TimeSeriesFloat,
        periods: Periods,
        actual_period: Period,
    ) -> NDArray[np.float64]:
        result = np.full_like(power_requirement.values, fill_value=np.nan).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                start_index, end_index = period.get_period_indices(periods)
                result[start_index:end_index] = model.evaluate(
                    np.asarray(power_requirement.values[start_index:end_index])
                )
        return result

    def evaluate_power_capacity_margin(
        self,
        power_requirement: TimeSeriesFloat,
        periods: Periods,
        actual_period: Period,
    ) -> NDArray[np.float64]:
        result = np.zeros_like(power_requirement.values).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                start_index, end_index = period.get_period_indices(periods)
                result[start_index:end_index] = model.evaluate_power_capacity_margin(
                    np.asarray(power_requirement.values[start_index:end_index])
                )
        return result
