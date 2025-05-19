from __future__ import annotations

from abc import abstractmethod
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
from scipy.interpolate import interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.units import Unit, UnitConstants
from libecalc.domain.process.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.domain.process.core.results import PumpModelResult

EPSILON = 1e-15


class PumpModel:
    fluid_required = True
    pressures_required = True

    def __init__(
        self,
        _max_flow_func: interp1d = None,
    ):
        self._max_flow_func = _max_flow_func

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_density: NDArray[np.float64] | float = 1,
    ) -> NDArray[np.float64]:
        """:param suction_pressures: Suction pressure per time-step
        :param discharge_pressures: Discharge pressure per time-step
        :param fluid_density:
            The density of the fluid used to convert to standard volume. None assumes non-compressibility

        :return: Maximum standard rate per day [Sm3/day] per time-step
        """
        density = fluid_density
        head = self._calculate_head(ps=suction_pressures, pd=discharge_pressures, density=density)
        max_rate = self._max_flow_func(head) * UnitConstants.HOURS_PER_DAY

        return np.array(max_rate)

    @abstractmethod
    def evaluate_rate_ps_pd_density(
        self,
        rate: NDArray[np.float64],
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_density: NDArray[np.float64],
    ) -> PumpModelResult:
        pass

    @staticmethod
    def _calculate_head(
        ps: NDArray[np.float64] | list[float],
        pd: NDArray[np.float64] | list[float],
        density: NDArray[np.float64] | float,
    ) -> NDArray[np.float64]:
        """:return: Head in joule per kg [J/kg]"""
        ps = np.array(ps, dtype=np.float64)
        pd = np.array(pd, dtype=np.float64)
        return np.array(Unit.BARA.to(Unit.PASCAL)(pd - ps) / density)

    @staticmethod
    def _calculate_power(
        densities: NDArray[np.float64],
        heads_joule_per_kg: NDArray[np.float64],
        efficiencies: NDArray[np.float64] | float,
        rates: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate pump power in MW from densities, heads, rates and efficiencies
        heads [J/kg].
        """
        return np.array(
            densities
            * heads_joule_per_kg
            * rates
            / UnitConstants.SECONDS_PER_HOUR
            / UnitConstants.WATT_PER_MEGAWATT
            / efficiencies
        )


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class PumpModelDTO:
    energy_usage_adjustment_constant: float
    energy_usage_adjustment_factor: float
    chart: SingleSpeedChartDTO | VariableSpeedChartDTO
    head_margin: float
    typ: Literal[EnergyModelType.PUMP_MODEL] = EnergyModelType.PUMP_MODEL


class PumpSingleSpeed(PumpModel):
    def __init__(
        self,
        pump_chart: SingleSpeedChart,
        head_margin: float = 0.0,
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ):
        """:param pump_chart:
        :param energy_usage_adjustment_constant: a constant to be added to the computed power
        :param energy_usage_adjustment_factor: a factor to be multiplied to computed power
        :param head_margin:
            a margin for accepting head values above maximum head from pump chart.
            Values above within margin will be set to maximum.
        """
        super().__init__()
        self.pump_chart = pump_chart
        self._head_margin = head_margin
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor

        self._max_flow_func = pump_chart.rate_as_function_of_head

    def evaluate_rate_ps_pd_density(
        self,
        rate: NDArray[np.float64],
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_density: NDArray[np.float64],
    ) -> PumpModelResult:
        """:param rate: Stream day rate. Must be converted from calendar_day_rate using regularity
        :param suction_pressures:
        :param discharge_pressures:
        :param fluid_density:
        """
        # Ensure rate is a NumPy array
        rate = np.asarray(rate, dtype=np.float64)
        fluid_density = np.asarray(fluid_density, dtype=np.float64)

        # Ensure that the pump does not run when rate is <= 0.
        stream_day_rate = np.where(rate > 0, rate, 0)

        # Reservoir rates: m3/day, pumpchart rates: m3/h
        rates_m3_per_hour = stream_day_rate / UnitConstants.HOURS_PER_DAY

        # Rates less than min to min rate (recirc)
        rates_m3_per_hour = np.fmax(rates_m3_per_hour, self.pump_chart.minimum_rate)

        # Head [J/kg]
        operational_heads = self._calculate_head(ps=suction_pressures, pd=discharge_pressures, density=fluid_density)

        # Single speed: calculate actual pump head [[J/kg]]
        actual_heads = self.pump_chart.head_as_function_of_rate(rates_m3_per_hour)

        # Allowed calculation points is where required head is less than or equal to actual pump head
        # and rates are less than or equal to maximum pump rate
        allowed_points = np.argwhere(
            (rates_m3_per_hour <= self.pump_chart.maximum_rate)
            & (operational_heads <= actual_heads + self._head_margin)
        )[:, 0]

        efficiency = self.pump_chart.efficiency_as_function_of_rate(rates_m3_per_hour[allowed_points])

        power = np.full_like(rates_m3_per_hour, fill_value=np.nan)
        power[allowed_points] = self._calculate_power(
            densities=fluid_density[allowed_points],
            heads_joule_per_kg=actual_heads[allowed_points],
            rates=rates_m3_per_hour[allowed_points],
            efficiencies=efficiency,
        )

        # Ensure that the pump does not run when rate is <= 0, while keeping intermediate calculated data for QA.
        power = np.where(rate > 0, power, 0)

        power_out = transform_linear(
            values=power,
            constant=self._energy_usage_adjustment_constant,
            factor=self._energy_usage_adjustment_factor,
        )

        pump_result = PumpModelResult(
            energy_usage=list(power_out),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_out),
            power_unit=Unit.MEGA_WATT,
            rate=list(rate),
            suction_pressure=list(suction_pressures),
            discharge_pressure=list(discharge_pressures),
            fluid_density=list(fluid_density),
            operational_head=list(operational_heads),
        )

        return pump_result


class PumpVariableSpeed(PumpModel):
    """Create variable speed pump.

    :param pump_chart: data for pump chart with headers SPEED, HEAD, RATE, EFFICIENCY
    :type pump_chart: PumpChartVariableSpeed
    :param energy_usage_adjustment_constant: a constant to be added to the computed power
    :type energy_usage_adjustment_constant: float
    :param energy_usage_adjustment_factor: a factor to be multiplied to computed power
    :type energy_usage_adjustment_factor: float
    :param head_margin:
        a margin for accepting head values above maximum head from pump chart.
        Values above within margin will be set to maximum.
    :type head_margin: float
    """

    def __init__(
        self,
        pump_chart: VariableSpeedChart,
        head_margin: float = 0.0,
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ):
        super().__init__()
        self.pump_chart = pump_chart
        self._head_margin = head_margin
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self._max_flow_func = pump_chart.maximum_rate_as_function_of_head

    def evaluate_rate_ps_pd_density(
        self,
        rate: NDArray[np.float64],
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_density: NDArray[np.float64],
    ) -> PumpModelResult:
        """Simulate a single pump with variable speed.

        Negative or 0 rate will be set to np.nan if :param set_zero_rates_to_zero is set to True.
        Points in the 2D chart from a given rate and head [J/kg] (ps, pd, density) that are outside the envelope
        (working area of a pump), will also be set to np.nan indicating that the pump are not able to handle the given
        parameters. This is sometimes the case if incorrect data is provided, but most often in a pump system where x
        pumps are not able to handle the given input. This is fine, but user should be notified.

        :param rate: Stream day rate [m3/day]
        :param suction_pressures:
        :param discharge_pressures:
        :param fluid_density:
        """
        stream_day_rate = np.where(rate > 0, rate, np.nan)

        # Reservoir rates: m3/day, pumpchart rates: m3/h
        rates_m3_per_hour = stream_day_rate / UnitConstants.HOURS_PER_DAY

        # Head [J/kg] calculation (for pump  with density).
        operational_heads = self._calculate_head(ps=suction_pressures, pd=discharge_pressures, density=fluid_density)

        # Adjust rates according to minimum flow line (recirc left of this line)
        minimum_flow_at_head = self.pump_chart.minimum_rate_as_function_of_head(operational_heads)
        rates_m3_per_hour = np.fmax(rates_m3_per_hour, minimum_flow_at_head + EPSILON)

        # Adjust head according to minimum head line (choking below this line)
        minimum_head_at_rate = self.pump_chart.minimum_head_as_function_of_rate(rates_m3_per_hour)
        heads = np.fmax(operational_heads, minimum_head_at_rate + EPSILON)

        maximum_head_at_rate = self.pump_chart.maximum_head_as_function_of_rate(rates_m3_per_hour)

        heads = _adjust_for_head_margin(
            heads=heads,
            maximum_heads=maximum_head_at_rate,
            head_margin=self._head_margin,
        )

        """
        Find (rate, head) points inside envelope (indices of the points that are within the working area
        and can be calculated) Those that fall outside the working area, means that this pump(s) is not able to handle
        those rates/heads (alone)
        """
        points_in_envelope: NDArray[np.float64] = np.argwhere(
            (rates_m3_per_hour <= self.pump_chart.maximum_rate) & (heads <= maximum_head_at_rate)
        )[:, 0]
        logger.debug(
            f"Filtered out {len(rates_m3_per_hour) - len(points_in_envelope)} "
            f"points due to being outside envelope for current pump."
        )

        power_before_efficiency_is_applied = np.full_like(rates_m3_per_hour, fill_value=np.nan)
        power_after_efficiency_is_applied = power_before_efficiency_is_applied.copy()
        if points_in_envelope.size:
            logger.debug(f"Calculating power and efficiency for {len(points_in_envelope)} points inside envelope.")
            # Calculate power for points within working area of pump(s)
            power_before_efficiency_is_applied[points_in_envelope] = self._calculate_power(
                densities=fluid_density[points_in_envelope],
                heads_joule_per_kg=heads[points_in_envelope],
                rates=rates_m3_per_hour[points_in_envelope],
                efficiencies=1,
            )

            if not self.pump_chart.is_100_percent_efficient:
                # If we do not have 100% (...) efficiency for pumps,
                # interpolate and find efficiency based on input pump chart

                efficiencies = np.full_like(power_after_efficiency_is_applied, fill_value=np.nan)
                efficiencies[points_in_envelope] = self.pump_chart.efficiency_as_function_of_rate_and_head(
                    rates=rates_m3_per_hour[points_in_envelope],
                    heads=heads[points_in_envelope],
                )

                power_after_efficiency_is_applied = power_before_efficiency_is_applied / efficiencies

        # Ensure that the pump does not run when rate is <= 0, while keeping intermediate calculated data for QA.
        power = np.where(rate > 0, power_after_efficiency_is_applied, 0)

        power_out = transform_linear(
            values=power,
            constant=self._energy_usage_adjustment_constant,
            factor=self._energy_usage_adjustment_factor,
        )
        pump_result = PumpModelResult(
            energy_usage=list(power_out),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_out),
            power_unit=Unit.MEGA_WATT,
            rate=list(rate),
            suction_pressure=list(suction_pressures),
            discharge_pressure=list(discharge_pressures),
            fluid_density=list(fluid_density),
            operational_head=list(operational_heads),
        )

        return pump_result


def _adjust_for_head_margin(heads: NDArray[np.float64], maximum_heads: NDArray[np.float64], head_margin: float):
    """A method which adjust heads and set head equal to maximum head if head is above maximum
    but below maximum + head margin.

    :param heads: head values [J/kg]
    :param maximum_heads: maximum head values [J/kg]
    :param head_margin: the margin for how much above maximum the head values are set equal to maximum [J/kg]
    """
    heads_adjusted = np.reshape(heads, -1).copy()
    maximum_heads_reshaped = np.reshape(maximum_heads, -1)
    if head_margin:
        indices_heads_inside_margin = np.argwhere(
            (heads_adjusted > maximum_heads_reshaped) & (heads_adjusted <= maximum_heads_reshaped + head_margin)
        )[:, 0]
        heads_adjusted[indices_heads_inside_margin] = maximum_heads_reshaped[indices_heads_inside_margin]
    return heads_adjusted
