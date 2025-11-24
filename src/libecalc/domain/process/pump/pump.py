from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.units import Unit, UnitConstants
from libecalc.domain.process.core.results import PumpModelResult
from libecalc.domain.process.core.results.pump import PumpFailureStatus
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.process.value_objects.chart.chart import ChartData

EPSILON = 1e-15


class PumpModel:
    """Create a Pump instance.

    Args:
        pump_chart (ChartData): Data for pump chart with speed, head, rate and efficiency
        head_margin (float, optional): Margin for accepting head values above maximum head from pump chart.
            Values above within margin will be set to maximum. Defaults to 0.0.
        energy_usage_adjustment_constant (float, optional): Constant to be added to the computed power. Defaults to 0.0.
        energy_usage_adjustment_factor (float, optional): Factor to be multiplied to computed power. Defaults to 1.0.
    """

    def __init__(
        self,
        pump_chart: ChartData,
        head_margin: float = 0.0,
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ):
        assert isinstance(pump_chart, ChartData)
        self._pump_chart = Chart(pump_chart)
        self._head_margin = head_margin
        self._energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self._energy_usage_adjustment_factor = energy_usage_adjustment_factor

    def get_max_standard_rates(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_densities: NDArray[np.float64] | float = 1.0,
    ) -> NDArray[np.float64]:
        """
        Get maximum standard rate per day [Sm3/day] per time-step

        Args:
            suction_pressures (NDArray[np.float64]): Suction pressure per time-step.
            discharge_pressures (NDArray[np.float64]): Discharge pressure per time-step.
            fluid_densities (NDArray[np.float64] or float, optional): The density of the fluid used to convert to standard volume.

        Returns:
            NDArray[np.float64]: Maximum standard rate per day [Sm3/day] per time-step.
        """

        if isinstance(fluid_densities, float):
            fluid_densities = np.full_like(suction_pressures, fluid_densities)

        assert len(suction_pressures) == len(discharge_pressures) == len(fluid_densities)

        max_rates = []
        for suction_pressure, discharge_pressure, density in zip(
            suction_pressures, discharge_pressures, fluid_densities
        ):
            max_rate = self.get_max_standard_rate(
                suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, fluid_density=density
            )
            max_rates.append(max_rate)

        return np.asarray(max_rates)

    def get_max_standard_rate(
        self,
        suction_pressure: float,
        discharge_pressure: float,
        fluid_density: float = 1.0,
    ) -> float:
        """
        Get maximum standard rate per day [Sm3/day] with given suction and discharge pressures.

        Args:
            suction_pressure (float): Suction pressure BarA.
            discharge_pressure (float): Discharge pressure BarA.
            fluid_density (float, optional): The density of the fluid used to convert to standard volume. Defaults to 1.0. Assumes non-compressibility if None.

        Returns:
            float: Maximum standard rate per day [Sm3/day]
        """
        head = self._calculate_head(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, density=fluid_density
        )
        max_rate = self._pump_chart.maximum_rate_as_function_of_head(head) * UnitConstants.HOURS_PER_DAY

        return max_rate

    @staticmethod
    def _calculate_head(
        suction_pressure: float,
        discharge_pressure: float,
        density: float,
    ) -> float:
        """:return: Head in joule per kg [J/kg]"""

        return Unit.BARA.to(Unit.PASCAL)(discharge_pressure - suction_pressure) / density

    @staticmethod
    def _calculate_power(
        density: float,
        head_joule_per_kg: float,
        efficiency: float,
        rate: float,
    ) -> float:
        """Calculate pump power in MW from densitiy, head, rate and efficiency
        head [J/kg].
        """
        return (
            density
            * head_joule_per_kg
            * rate
            / UnitConstants.SECONDS_PER_HOUR
            / UnitConstants.WATT_PER_MEGAWATT
            / efficiency
        )

    def evaluate_rate_ps_pd_density(
        self,
        rates: NDArray[np.float64],
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        fluid_densities: NDArray[np.float64],
    ) -> PumpModelResult:
        """
        Legacy method to evaluate pump model with arrays of rates, suction pressures, discharge pressures and fluid densities.
        Args:
            rates:
            suction_pressures:
            discharge_pressures:
            fluid_densities:

        Returns:

        """
        assert len(rates) == len(suction_pressures) == len(discharge_pressures) == len(fluid_densities)

        power_out_array = []
        operational_heads = []
        failure_statuses = []
        for rate, suction_pressure, discharge_pressure, density in zip(
            rates, suction_pressures, discharge_pressures, fluid_densities
        ):
            power_out, operational_head, failure_status = self.simulate(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                fluid_density=density,
            )
            power_out_array.append(power_out)
            operational_heads.append(operational_head)
            failure_statuses.append(failure_status)

        return PumpModelResult(
            energy_usage=power_out_array,
            energy_usage_unit=Unit.MEGA_WATT,
            power=power_out_array,
            power_unit=Unit.MEGA_WATT,
            rate=list(rates),
            suction_pressure=list(suction_pressures),
            discharge_pressure=list(discharge_pressures),
            fluid_density=list(fluid_densities),
            operational_head=operational_heads,
            failure_status=failure_statuses,
        )

    def simulate(
        self,
        rate: float,
        suction_pressure: float,
        discharge_pressure: float,
        fluid_density: float,
    ) -> tuple[float, float, PumpFailureStatus]:
        """Simulate a single pump with fixed speed (speed is not relevant, and therefore not included in the parameters).

        Points in the 2D chart from a given rate and head [J/kg] (ps, pd, density) that are outside the envelope
        (working area of a pump), will be set to math.nan indicating that the pump is not able to handle the given
        parameters. This is sometimes the case if incorrect data is provided, but most often in a pump system where x
        pumps are not able to handle the given input. This is fine, but user should be notified.

        However, if head margin is set, and the head is above maximum head at rate but within head margin, the head is set to maximum head.

        If rate is less than or equal to zero, the pump is considered not running, and power and head are set to zero. However, it is not considered a failure.

        :param rate: Stream day rate [m3/day]
        :param suction_pressure:   BarA
        :param discharge_pressure: BarA
        :param fluid_density: kg/m3

        :return: power [MW], head [J/kg], failure status
        """
        if rate <= 0:
            return self._energy_usage_adjustment_constant, 0.0, PumpFailureStatus.NO_FAILURE

        # Reservoir rates: m3/day, pumpchart rates: m3/h
        rate_m3_per_hour = rate / UnitConstants.HOURS_PER_DAY

        # Head [J/kg] calculation (for pump  with density).
        operational_head = self._calculate_head(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, density=fluid_density
        )

        # Adjust rates according to minimum flow line (recirc left of this line)
        minimum_flow_at_head = float(self._pump_chart.minimum_rate_as_function_of_head(operational_head))
        rate_m3_per_hour = max(rate_m3_per_hour, minimum_flow_at_head + EPSILON)

        # Adjust head according to minimum head line (choking below this line)
        minimum_head_at_rate = float(self._pump_chart.minimum_head_as_function_of_rate(rate_m3_per_hour))
        head = max(operational_head, minimum_head_at_rate + EPSILON)

        maximum_head_at_rate = self._pump_chart.maximum_head_as_function_of_rate(rate_m3_per_hour)

        head = _adjust_for_head_margin(
            head=head,
            maximum_head=maximum_head_at_rate,
            head_margin=self._head_margin,
        )

        """
        Find (rate, head) points inside envelope (indices of the points that are within the working area
        and can be calculated) Those that fall outside the working area, means that this pump(s) is not able to handle
        those rates/heads (alone)
        """
        failure_status = (
            PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE
            if (head > maximum_head_at_rate and rate_m3_per_hour > self._pump_chart.maximum_rate)
            else PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE
            if head > maximum_head_at_rate
            else PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE
            if rate_m3_per_hour > self._pump_chart.maximum_rate
            else PumpFailureStatus.NO_FAILURE
        )

        logger.debug("Calculating power and efficiency.")
        # Calculate power for points within working area of pump(s)
        power_before_efficiency_is_applied = self._calculate_power(
            density=fluid_density,
            head_joule_per_kg=head,
            rate=rate_m3_per_hour,
            efficiency=1,
        )

        power = power_before_efficiency_is_applied
        if not self._pump_chart.is_100_percent_efficient:
            efficiency = self._pump_chart.efficiency_as_function_of_rate_and_head(
                rates=np.asarray([rate_m3_per_hour]),
                heads=np.asarray([head]),
            )
            power = power_before_efficiency_is_applied / efficiency[0]

        power_out = power * self._energy_usage_adjustment_factor + self._energy_usage_adjustment_constant

        return power_out, operational_head, failure_status

    def set_evaluation_input(
        self,
        stream_day_rate: NDArray[np.float64],
        fluid_density: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ):
        self._stream_day_rate = stream_day_rate
        self._fluid_density = fluid_density
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure

    def evaluate(self) -> PumpModelResult:
        # Do not input regularity to pump function. Handled outside
        pump_model_result = self.evaluate_rate_ps_pd_density(
            rates=self._stream_day_rate,
            suction_pressures=self._suction_pressure,
            discharge_pressures=self._discharge_pressure,
            fluid_densities=self._fluid_density,
        )
        return pump_model_result


def _adjust_heads_for_head_margin(
    heads: NDArray[np.float64], maximum_heads: NDArray[np.float64], head_margin: float
) -> NDArray[np.float64]:
    """A method which adjust heads and set head equal to maximum head if head is above maximum
    but below maximum + head margin.

    :param heads: head values [J/kg]
    :param maximum_heads: maximum head values [J/kg]
    :param head_margin: the margin for how much above maximum the head values are set equal to maximum [J/kg]
    """
    assert len(heads) == len(maximum_heads)

    heads_adjusted = []
    for head, maximum_head in zip(heads, maximum_heads):
        adjusted_head = _adjust_for_head_margin(head, maximum_head, head_margin)
        heads_adjusted.append(adjusted_head)

    return np.asarray(heads_adjusted)


def _adjust_for_head_margin(head: float, maximum_head: float, head_margin: float) -> float:
    """A method which adjust head and set head equal to maximum head if head is above maximum
    but below maximum + head margin.

    :param head: head value [J/kg]
    :param maximum_head: maximum head value [J/kg]
    :param head_margin: the margin for how much above maximum the head value are set equal to maximum [J/kg]
    """

    if head_margin:
        if (head > maximum_head) and (head <= maximum_head + head_margin):
            head = maximum_head
    return head
