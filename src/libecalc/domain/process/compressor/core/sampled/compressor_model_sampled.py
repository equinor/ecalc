from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_1d import (
    CompressorModelSampled1D,
)
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_2d import (
    CompressorModelSampled2DPsPd,
    CompressorModelSampled2DRatePd,
    CompressorModelSampled2DRatePs,
)
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_3d import (
    CompressorModelSampled3D,
)
from libecalc.domain.process.compressor.core.sampled.constants import (
    EPSILON,
    FUNCTION_VALUE_HEADER,
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)
from libecalc.domain.process.compressor.dto import CompressorSampled
from libecalc.domain.process.core.results import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainResult,
    TurbineResult,
)
from libecalc.domain.process.core.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)


class CompressorModelSampled(CompressorModel):
    """Compressor/pump energy function based on sampled data
    There may be one to three variables which may be rate, suction_pressure and discharge_pressure
    The function value must be power or fuel.
    Inside the convex hull of the input data, the data is linearly interpolated. Outside the
    input_data, there are extrapolations consistent with ASV and choking.
    """

    fluid_required: bool = False

    def __init__(
        self,
        data_transfer_object: CompressorSampled,
    ):
        """Nomenclature:
        function_values: array containing the function values
        power_interpolation_values: if fuel is given as function_values, and the user also needs power values
            (since a fuel driven compressor is an abstraction of a compressor with a (gas) turbine).
            Often needed for energy reporting in e.g. LTP, STP.
        """
        logger.debug("Creating CompressorModelSampled")
        self.data_transfer_object = data_transfer_object
        self.function_values_are_power = self.data_transfer_object.energy_usage_type == EnergyUsageType.POWER
        self.power_interpolation_values = data_transfer_object.power_interpolation_values

        function_values_adjusted: NDArray[np.float64] = transform_linear(
            values=np.reshape(np.array(data_transfer_object.energy_usage_values).astype(float), -1),
            constant=data_transfer_object.energy_usage_adjustment_constant,
            factor=data_transfer_object.energy_usage_adjustment_factor,
        )

        self.fuel_values_adjusted: NDArray[np.float64] | None = None
        self.power_interpolation_values_adjusted: NDArray[np.float64] | None = None
        if not self.function_values_are_power and self.power_interpolation_values:
            self.fuel_values_adjusted = function_values_adjusted
            self.power_interpolation_values_adjusted = transform_linear(
                values=np.reshape(self.power_interpolation_values, -1),
                constant=data_transfer_object.energy_usage_adjustment_constant,
                factor=data_transfer_object.energy_usage_adjustment_factor,
            )

        variables: dict[str, list[float]] = {}
        if data_transfer_object.rate_values is not None:
            variables[RATE_NAME] = data_transfer_object.rate_values
        if data_transfer_object.suction_pressure_values is not None:
            variables[PS_NAME] = data_transfer_object.suction_pressure_values
        if data_transfer_object.discharge_pressure_values is not None:
            variables[PD_NAME] = data_transfer_object.discharge_pressure_values

        self.required_variables = list(variables.keys())

        function_value_header = "ENERGY_USAGE"
        sampled_data = pd.DataFrame(np.asarray(list(variables.values()) + [list(function_values_adjusted)]).transpose())
        sampled_data.columns = list(variables.keys()) + [function_value_header]

        apparent_dimension: int = len(self.required_variables)
        non_degenerated_variables: list[str] = self._non_degenerated_variables(sampled_data[self.required_variables])
        geometric_dimension: int = len(non_degenerated_variables)
        degenerated_variables: list[str] = (
            [var for var in self.required_variables if var not in non_degenerated_variables]
            if geometric_dimension != apparent_dimension
            else []
        )

        """
        Set degenerated values for each variable. The values are used for comparison
        when evaluated, rates and pds need to be smaller than degenerated value and
        ps-s need to be larger. Thus if the function is not degenerated in that variable
        these are set to inf or -inf respectively.
        """
        self._degenerated_rate = sampled_data[RATE_NAME][0] if RATE_NAME in degenerated_variables else np.inf
        self._degenerated_ps = sampled_data[PS_NAME][0] if PS_NAME in degenerated_variables else -np.inf
        self._degenerated_pd = sampled_data[PD_NAME][0] if PD_NAME in degenerated_variables else np.inf

        """
        To be used for validation
        If CROSSOVER is used, the function needs to support get_max_standard_rate
        """
        self.support_max_rate: bool = RATE_NAME in self.required_variables

        qhull_compressor_model = self._get_compressor_model(geometric_dimension, non_degenerated_variables)
        sampled_data_input = sampled_data[non_degenerated_variables + [function_value_header]]
        self._qhull_sampled = qhull_compressor_model(
            sampled_data=sampled_data_input,
            function_header=FUNCTION_VALUE_HEADER,
        )

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64] | None = None,
        discharge_pressures: NDArray[np.float64] | None = None,
    ) -> NDArray[np.float64] | None:
        """Get max rate given suction pressure and a discharge pressure.

        :param suction_pressures: Suction pressure [bar]
        :param discharge_pressures: Discharge pressure [bar]
        """
        number_of_calculation_points = len(suction_pressures) if suction_pressures is not None else 1
        if self.support_max_rate:
            if self._qhull_sampled.support_max_rate:
                return np.full(
                    shape=number_of_calculation_points,
                    fill_value=self._qhull_sampled.get_max_rate(),
                )
            else:
                return np.full(shape=number_of_calculation_points, fill_value=self._degenerated_rate)
        else:
            return np.full(shape=number_of_calculation_points, fill_value=np.nan)

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ) -> CompressorTrainResult:
        """
        Evaluate the compressor model to calculate energy usage, power, and other results.

        Args:
            rate (NDArray[np.float64]): Actual volumetric flow rate in [Sm3/h] for each time step.
            suction_pressure (NDArray[np.float64]): Suction pressure in [bara] for each time step.
            discharge_pressure (NDArray[np.float64]): Discharge pressure in [bara] for each time step.
            intermediate_pressure (NDArray[np.float64] | None): Intermediate pressure in [bara] for each time step, or None.

        Returns:
            CompressorTrainResult: The result of the compressor train evaluation, including energy usage, power, and other metrics.
        """
        # subtract an epsilon to make robust comparison.
        if rate is not None:
            # Ensure rate is a NumPy array
            rate = np.array(rate, dtype=np.float64)
            # To avoid bringing rate below zero.
            rate = np.where(rate > 0, rate - EPSILON, rate)
        if suction_pressure is not None:
            suction_pressure = np.array(suction_pressure, dtype=np.float64)

        if discharge_pressure is not None:
            discharge_pressure = np.array(discharge_pressure, dtype=np.float64)

        number_of_data_points = 0
        if rate is not None:
            number_of_data_points = rate.size
        elif suction_pressure is not None:
            number_of_data_points = suction_pressure.size
        elif discharge_pressure is not None:
            number_of_data_points = discharge_pressure.size

        # Initialize result with nan
        interpolated_consumer_values = np.full((number_of_data_points,), np.nan)

        if rate is not None:
            # Find indices where rate is zero and set result to zero (zero rate means machine is off)
            zero_rate = list(rate <= 0 if rate is not None else False)
            indices_set_to_zero = self._get_indices_from_condition(condition=zero_rate)
            interpolated_consumer_values[indices_set_to_zero] = 0.0

        """
        Find indices to evaluate from interpolator
        These are where rate is positive and potentially degenerated variables are accounted for
        """
        rate_is_positive = rate > 0 if rate is not None else True
        degenerated_rate_ok = rate <= self._degenerated_rate if rate is not None else True
        degenerated_ps_ok = suction_pressure >= self._degenerated_ps if suction_pressure is not None else True
        degenerated_pd_ok = discharge_pressure <= self._degenerated_pd if discharge_pressure is not None else True

        indices_to_evaluate = self._get_indices_from_condition(
            condition=rate_is_positive & degenerated_rate_ok & degenerated_ps_ok & degenerated_pd_ok
        )

        rate_to_evaluate = rate[indices_to_evaluate] if rate is not None else []
        ps_to_evaluate = suction_pressure[indices_to_evaluate] if suction_pressure is not None else []
        pd_to_evaluate = discharge_pressure[indices_to_evaluate] if discharge_pressure is not None else []

        interpolated_consumer_values[indices_to_evaluate] = self._qhull_sampled.evaluate(
            rate=rate_to_evaluate,
            suction_pressure=ps_to_evaluate,
            discharge_pressure=pd_to_evaluate,
        )

        turbine = self.Turbine(self.fuel_values_adjusted, self.power_interpolation_values_adjusted)
        turbine_result = turbine.calculate_turbine_power_usage(interpolated_consumer_values)
        turbine_power = turbine_result.load if turbine_result is not None else None

        energy_usage = (
            turbine_result.energy_usage if turbine_result is not None else array_to_list(interpolated_consumer_values)
        )

        inlet_stream_condition = CompressorStreamCondition.create_empty(number_of_periods=number_of_data_points)
        inlet_stream_condition.pressure = (
            array_to_list(suction_pressure) if suction_pressure is not None else [np.nan] * number_of_data_points
        )

        outlet_stream_condition = CompressorStreamCondition.create_empty(number_of_periods=number_of_data_points)
        outlet_stream_condition.pressure = (
            array_to_list(discharge_pressure) if discharge_pressure is not None else [np.nan] * number_of_data_points
        )

        compressor_stage_result = CompressorStageResult.create_empty(number_of_periods=number_of_data_points)
        if energy_usage is not None:
            compressor_stage_result.energy_usage = energy_usage
        compressor_stage_result.energy_usage_unit = (
            Unit.MEGA_WATT if self.function_values_are_power else Unit.STANDARD_CUBIC_METER_PER_DAY
        )
        compressor_stage_result.power = (
            array_to_list(interpolated_consumer_values) if self.function_values_are_power else turbine_power
        )
        compressor_stage_result.power_unit = Unit.MEGA_WATT
        compressor_stage_result.inlet_stream_condition = inlet_stream_condition
        compressor_stage_result.outlet_stream_condition = outlet_stream_condition
        compressor_stage_result.fluid_composition = {}
        compressor_stage_result.chart = None
        compressor_stage_result.is_valid = array_to_list(
            np.logical_and(~np.isnan(energy_usage), turbine_result.is_valid)
            if turbine_result is not None
            else ~np.isnan(energy_usage)
        )
        compressor_stage_result.chart_area_flags = [ChartAreaFlag.NOT_CALCULATED] * len(energy_usage)
        compressor_stage_result.rate_has_recirculation = [False] * len(energy_usage)
        compressor_stage_result.rate_exceeds_maximum = [False] * len(energy_usage)
        compressor_stage_result.pressure_is_choked = [False] * len(energy_usage)
        compressor_stage_result.head_exceeds_maximum = [False] * len(energy_usage)
        compressor_stage_result.asv_recirculation_loss_mw = [0.0] * len(energy_usage)

        # Returning a result as if the sampled compressor is a train with a single stage.
        # Note that actual rates are not available since it is not possible to convert from standard rates to
        # actual rates when information about fluid composition (density in particular) is not available
        result = CompressorTrainResult(
            inlet_stream_condition=inlet_stream_condition,
            outlet_stream_condition=outlet_stream_condition,
            energy_usage=energy_usage,
            energy_usage_unit=Unit.MEGA_WATT if self.function_values_are_power else Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=array_to_list(interpolated_consumer_values) if self.function_values_are_power else turbine_power,
            power_unit=Unit.MEGA_WATT,
            stage_results=[compressor_stage_result],
            failure_status=[CompressorTrainCommonShaftFailureStatus.NO_FAILURE] * len(energy_usage),
            rate_sm3_day=array_to_list(rate) if rate is not None else [np.nan] * len(energy_usage),
        )

        return result

    @staticmethod
    def _get_indices_from_condition(condition: list[bool]) -> list[int]:
        """Return the indices in a list with booleans where the value is True."""
        return np.argwhere(condition)[:, 0]

    @staticmethod
    def _get_compressor_model(
        geometric_dimension: int, non_degenerated_variables: list[str]
    ) -> (
        type[CompressorModelSampled1D]
        | type[CompressorModelSampled2DRatePd]
        | type[CompressorModelSampled2DRatePs]
        | type[CompressorModelSampled2DPsPd]
        | type[CompressorModelSampled3D]
    ):
        if geometric_dimension == 3:
            return CompressorModelSampled3D
        elif geometric_dimension == 1:
            return CompressorModelSampled1D
        elif geometric_dimension == 2:
            if RATE_NAME not in non_degenerated_variables:
                return CompressorModelSampled2DPsPd
            elif PS_NAME not in non_degenerated_variables:
                return CompressorModelSampled2DRatePd
            elif PD_NAME not in non_degenerated_variables:
                return CompressorModelSampled2DRatePs
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

    @staticmethod
    def _non_degenerated_variables(sampled_data: pd.DataFrame) -> list[str]:
        """

        Args:
            sampled_data:

        Returns:
           list of non degenerated values

        """
        uniques = sampled_data.apply(lambda x: x.nunique())
        return array_to_list(uniques[uniques != 1].index.values)

    @dataclass
    class Turbine:
        """In some cases we want to calculate the turbine power in a fuel-driven compressor sampled model, where the
        turbine has been abstracted away. Then we need an interpolation function between fuel and power.
        Hence, this class is currently only relevant in this compressor model sampled context.
        """

        fuel_values: NDArray[np.float64] | None
        power_values: NDArray[np.float64] | None

        def __post_init__(self) -> None:
            if (
                self.fuel_values is not None
                and self.power_values is not None
                and (len(self.fuel_values) == len(self.power_values))
            ):
                self.fuel_to_power_function = interp1d(
                    self.fuel_values,
                    self.power_values,
                    fill_value=(0, np.nan),
                    bounds_error=False,
                )
            else:
                self.fuel_to_power_function = None

        @Feature.experimental(
            feature_description="Calculate (turbine) power usage in fuel-driven compressor sampled model"
        )
        def calculate_turbine_power_usage(self, fuel_usage_values: NDArray[np.float64]) -> TurbineResult | None:
            if self.fuel_to_power_function is not None and fuel_usage_values is not None:
                load = self.fuel_to_power_function(fuel_usage_values)
                return TurbineResult(
                    fuel_rate=array_to_list(fuel_usage_values),
                    efficiency=array_to_list(np.ones_like(fuel_usage_values)),
                    load=array_to_list(load),
                    energy_usage=array_to_list(fuel_usage_values),
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=array_to_list(self.fuel_to_power_function(fuel_usage_values)),
                    power_unit=Unit.MEGA_WATT,
                    exceeds_maximum_load=array_to_list(np.isnan(load)),
                )

            # If power_values is not set, user is not interested in power usage, there is no error in that
            return None
