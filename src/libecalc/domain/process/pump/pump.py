from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from libecalc.common.list.adjustment import transform_linear
from libecalc.common.logger import logger
from libecalc.common.units import Unit, UnitConstants
from libecalc.domain.process.core.results import PumpModelResult
from libecalc.domain.process.core.results.pump import PumpFailureStatus
from libecalc.domain.process.value_objects.chart import Chart

EPSILON = 1e-15


class PumpModel:
    """Create a Pump instance.

    Args:
        pump_chart (Chart): Data for pump chart with speed, head, rate and efficiency
        head_margin (float, optional): Margin for accepting head values above maximum head from pump chart.
            Values above within margin will be set to maximum. Defaults to 0.0.
        energy_usage_adjustment_constant (float, optional): Constant to be added to the computed power. Defaults to 0.0.
        energy_usage_adjustment_factor (float, optional): Factor to be multiplied to computed power. Defaults to 1.0.
    """

    def __init__(
        self,
        pump_chart: Chart,
        head_margin: float,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        self.pump_chart = pump_chart
        self._head_margin = head_margin
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self._max_flow_func = pump_chart.maximum_rate_as_function_of_head

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_density: NDArray[np.float64] | float = 1,
    ) -> NDArray[np.float64]:
        """
        Args:
            suction_pressures (NDArray[np.float64]): Suction pressure per time-step.
            discharge_pressures (NDArray[np.float64]): Discharge pressure per time-step.
            fluid_density (NDArray[np.float64] or float, optional): The density of the fluid used to convert to standard volume. Defaults to 1. Assumes non-compressibility if None.

        Returns:
            NDArray[np.float64]: Maximum standard rate per day [Sm3/day] per time-step.
        """
        density = fluid_density
        head = self._calculate_head(ps=suction_pressures, pd=discharge_pressures, density=density)
        max_rate = self._max_flow_func(head) * UnitConstants.HOURS_PER_DAY

        return np.array(max_rate)

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
            maximum_heads=maximum_head_at_rate,  # type: ignore[arg-type]
            head_margin=self._head_margin,
        )

        """
        Find (rate, head) points inside envelope (indices of the points that are within the working area
        and can be calculated) Those that fall outside the working area, means that this pump(s) is not able to handle
        those rates/heads (alone)
        """
        failure_status = [
            PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE
            if (head > max_head and rate > self.pump_chart.maximum_rate)
            else PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE
            if head > max_head
            else PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE
            if rate > self.pump_chart.maximum_rate
            else PumpFailureStatus.NO_FAILURE
            for head, max_head, rate in zip(heads, maximum_head_at_rate, rates_m3_per_hour)
        ]

        power_before_efficiency_is_applied = np.full_like(rates_m3_per_hour, fill_value=np.nan)
        power_after_efficiency_is_applied = power_before_efficiency_is_applied.copy()

        logger.debug("Calculating power and efficiency.")
        # Calculate power for points within working area of pump(s)
        power_before_efficiency_is_applied = self._calculate_power(
            densities=fluid_density,
            heads_joule_per_kg=heads,
            rates=rates_m3_per_hour,
            efficiencies=1,
        )

        if not self.pump_chart.is_100_percent_efficient:
            efficiencies = self.pump_chart.efficiency_as_function_of_rate_and_head(
                rates=rates_m3_per_hour,
                heads=heads,
            )
            power_after_efficiency_is_applied = power_before_efficiency_is_applied / efficiencies

        # Ensure that the pump does not run when rate is <= 0, while keeping intermediate calculated data for QA.
        power = np.where(rate > 0, power_after_efficiency_is_applied, 0)

        power_out = transform_linear(
            values=power,
            constant=self._energy_usage_adjustment_constant,
            factor=self._energy_usage_adjustment_factor,
        )

        power_out_array = np.asarray(power_out, dtype=np.float64)

        pump_result = PumpModelResult(
            energy_usage=list(power_out_array),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_out_array),
            power_unit=Unit.MEGA_WATT,
            rate=list(rate),
            suction_pressure=list(suction_pressures),
            discharge_pressure=list(discharge_pressures),
            fluid_density=list(fluid_density),
            operational_head=list(operational_heads),
            failure_status=failure_status,
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
