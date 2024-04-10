import numpy as np
from numpy.typing import NDArray

from libecalc import dto
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
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import GeneratorSetResult
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression


class Genset:
    def __init__(
        self,
        data_transfer_object: dto.GeneratorSet,
    ):
        logger.debug(f"Creating Genset: {data_transfer_object.name}")
        self.data_transfer_object = data_transfer_object
        self.temporal_generator_set_model = TemporalModel(
            {
                start_time: GeneratorModelSampled(model)
                for start_time, model in data_transfer_object.generator_set_model.items()
            }
        )

    def evaluate(
        self,
        variables_map: VariablesMap,
        power_requirement: NDArray[np.float64],
    ) -> GeneratorSetResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid timesteps. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating Genset: {self.data_transfer_object.name}")

        if not len(power_requirement) == len(variables_map.time_vector):
            raise ValueError("length of power_requirement does not match the time vector.")

        # Compute fuel consumption from power rate.
        fuel_rate = self.evaluate_fuel_rate(power_requirement, variables_map=variables_map)
        power_capacity_margin = self.evaluate_power_capacity_margin(power_requirement, variables_map=variables_map)

        # Check if Power From Shore, if so do necessary calculations.
        if ConsumerUserDefinedCategoryType.POWER_FROM_SHORE in self.data_transfer_object.user_defined_category.values():
            # cable_loss = Expression.evaluate(
            #     self.data_transfer_object.cable_loss, variables=variables_map.variables, fill_length=len(variables_map.time_vector)
            # )
            # power_supply_onshore = power_requirement + cable_loss
            # max_usage_from_shore = Expression.evaluate(
            #     self.data_transfer_object.max_usage_from_shore, variables=variables_map.variables, fill_length=len(variables_map.time_vector)
            # )
            power_supply_onshore, max_usage_from_shore = self.evaluate_power_from_shore(
                power_requirement=power_requirement, variables_map=variables_map
            )
        else:
            power_supply_onshore = None
            max_usage_from_shore = None

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
            id=self.data_transfer_object.id,
            timesteps=variables_map.time_vector,
            is_valid=TimeSeriesBoolean(
                timesteps=variables_map.time_vector,
                values=array_to_list(valid_timesteps),
                unit=Unit.NONE,
            ),
            power_capacity_margin=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(power_capacity_margin),
                unit=Unit.MEGA_WATT,
            ),
            power=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(power_requirement),
                unit=Unit.MEGA_WATT,
            ),
            energy_usage=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(fuel_rate),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            power_supply_onshore=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(power_supply_onshore),
                unit=Unit.MEGA_WATT,
            )
            if power_supply_onshore is not None
            else None,
            max_usage_from_shore=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(max_usage_from_shore),
                unit=Unit.MEGA_WATT,
            )
            if max_usage_from_shore is not None
            else None,
        )

    def evaluate_fuel_rate(
        self, power_requirement: NDArray[np.float64], variables_map: dto.VariablesMap
    ) -> NDArray[np.float64]:
        result = np.full_like(power_requirement, fill_value=np.nan).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, variables_map.period):
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                result[start_index:end_index] = model.evaluate(power_requirement[start_index:end_index])
        return result

    def evaluate_power_capacity_margin(
        self, power_requirement: NDArray[np.float64], variables_map: dto.VariablesMap
    ) -> NDArray[np.float64]:
        result = np.zeros_like(power_requirement).astype(float)
        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, variables_map.period):
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                result[start_index:end_index] = model.evaluate_power_capacity_margin(
                    power_requirement[start_index:end_index]
                )
        return result

    def evaluate_power_from_shore(self, power_requirement: NDArray[np.float64], variables_map: dto.VariablesMap):
        cable_loss = Expression.evaluate(
            self.data_transfer_object.cable_loss,
            variables=variables_map.variables,
            fill_length=len(variables_map.time_vector),
        )

        max_usage_from_shore = Expression.evaluate(
            self.data_transfer_object.max_usage_from_shore,
            variables=variables_map.variables,
            fill_length=len(variables_map.time_vector),
        )
        result_power_supply_onshore = np.zeros_like(power_requirement).astype(float)
        result_max_usage_from_shore = np.zeros_like(max_usage_from_shore).astype(float)

        for model in self.temporal_generator_set_model.models:
            if Period.intersects(model.period, variables_map.period):
                start_index, end_index = model.period.get_timestep_indices(variables_map.time_vector)
                if (
                    self.data_transfer_object.user_defined_category[model.period.start]
                    == ConsumerUserDefinedCategoryType.POWER_FROM_SHORE
                ):
                    result_power_supply_onshore[start_index:end_index] = (power_requirement + cable_loss)[
                        start_index:end_index
                    ]
                else:
                    result_max_usage_from_shore[start_index:end_index] = 0.0
                result_max_usage_from_shore[start_index:end_index] = max_usage_from_shore[start_index:end_index]
        return result_power_supply_onshore, result_max_usage_from_shore
