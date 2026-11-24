"""A single-speed / variable-speed pump for an incompressible liquid.

The pump raises an inlet liquid stream toward a requested outlet pressure. The required head
follows directly from the pressure rise and the density (``head = (p_out - p_s) / rho``), and the
pump chart supplies the efficiency and the feasible operating window. Everything is closed-form:
the operating point is read off the chart envelope, so there is no solver and no iteration.

The operational head is the required head bounded by the chart at the operating rate:

- Required head below the chart's minimum head - a single-speed pump runs on its single curve,
  and a variable-speed pump cannot run below its minimum-speed curve. The pump runs at the
  minimum head, so its operational discharge pressure is above the requested outlet pressure.
  A downstream choke drops the difference (``choke_pressure_drop_bara``).
- Required head above the chart's maximum head - the pump runs at the maximum head, so its
  operational discharge pressure is below the requested outlet pressure
  (``pressure_shortfall_bara``). ``failure_status`` compares the required head with the maximum
  head, so it flags the result as infeasible.

The result exposes both the requested outlet pressure and the operational discharge pressure so a
caller can tell these regimes apart. The rate itself is never capped - only the head is. A rate
above the chart's own maximum rate is flagged separately, via
``PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE``. At such a rate, the head cap itself is also less
reliable: ``Chart.maximum_head_as_function_of_rate`` does not extrapolate the curve's declining
trend past its highest measured rate - it holds the head flat at the value from that highest-rate
point instead. For example, if the curve's highest-rate point is 927 m3/h, evaluating the pump at
1200 m3/h uses that same 927 m3/h head value as the cap.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

import numpy as np

from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.units import Unit, UnitConstants
from libecalc.process.chart import Chart
from libecalc.process.chart.chart import ChartData
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class PumpFailureStatus(StrEnum):
    NO_FAILURE = "NO_FAILURE"
    ABOVE_MAXIMUM_PUMP_RATE = "ABOVE_MAXIMUM_PUMP_RATE"
    ABOVE_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_HEAD_AT_RATE"
    ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE"


@value_object
class PumpEvaluationResult:
    """Result of a single pump evaluation.

    Attributes:
        inlet_stream: The liquid stream at suction conditions the pump was evaluated for
            (carries suction pressure, density and requested rate).
        shaft_power_mw: Shaft power [MW].
        efficiency: Pump efficiency at the operating point, ``None`` when not running.
        specific_shaft_work_joule_per_kg: Shaft work per unit mass at the operating point [J/kg],
            ``None`` when not running.
        required_head_joule_per_kg: Head implied by the suction and requested outlet pressures,
            ``(p_out - p_s) / rho`` [J/kg].
        operational_head_joule_per_kg: Head the pump runs at [J/kg]: the required head, raised to
            the chart's minimum head or lowered to its maximum head at the operating rate. Zero
            when not running.
        operational_volumetric_rate_m3_per_hour: Volumetric rate the pump operates at
            [m3/h], i.e. the requested rate raised to the minimum flow when recirculating.
        recirculation_rate_m3_per_hour: Internal recirculation [m3/h] to maintain the minimum flow
            = operational rate minus requested rate; zero when not recirculating.
        requested_outlet_pressure_bara: Pressure requested downstream of the choke [bara].
        operational_discharge_pressure_bara: Pressure at the pump discharge, upstream of the choke
            [bara], from the operational head. Above the requested outlet pressure when the
            required head is below the chart's minimum head (see ``choke_pressure_drop_bara``),
            below it when the required head is above the chart's maximum head (see
            ``pressure_shortfall_bara``).
        speed_rpm: Operating speed [rpm] of the pump (the speed curve through the operating point);
            the single curve's speed for a single-speed pump, ``None`` when not running.
        failure_status: ``NO_FAILURE`` unless the required head is above the chart's maximum head at
            the operating rate, or the operating rate is above the chart's maximum rate.
        process_unit_id: Identity of the pump that produced this result; lets a stored result be
            traced back to its pump (e.g. for persistence or a downstream energy calculation).
    """

    inlet_stream: LiquidStream
    shaft_power_mw: float
    efficiency: float | None
    specific_shaft_work_joule_per_kg: float | None
    required_head_joule_per_kg: float
    operational_head_joule_per_kg: float
    operational_volumetric_rate_m3_per_hour: float
    recirculation_rate_m3_per_hour: float
    requested_outlet_pressure_bara: float
    operational_discharge_pressure_bara: float
    speed_rpm: float | None
    failure_status: PumpFailureStatus
    process_unit_id: ProcessUnitId

    @property
    def is_valid(self) -> bool:
        return self.failure_status == PumpFailureStatus.NO_FAILURE

    @property
    def operational_outlet_pressure_bara(self) -> float:
        """Pressure downstream of a choke that drops the whole ``choke_pressure_drop_bara`` [bara].

        The requested outlet pressure, or the operational discharge pressure when that is lower. In a
        pump problem without a choke, the pressure downstream of the pump is the operational discharge
        pressure.
        """
        return min(self.operational_discharge_pressure_bara, self.requested_outlet_pressure_bara)

    @property
    def choke_pressure_drop_bara(self) -> float:
        """Pressure drop across a downstream choke that drops the whole difference [bara].

        Operational discharge pressure minus requested outlet pressure (>= 0). A running pump has a
        choke pressure drop when the required head is below the chart's minimum head at the
        operating rate. In a pump problem without a choke, nothing drops it.
        """
        return max(0.0, self.operational_discharge_pressure_bara - self.requested_outlet_pressure_bara)

    @property
    def pressure_shortfall_bara(self) -> float:
        """Pressure by which the pump falls short of the requested outlet pressure [bara].

        Requested outlet pressure minus operational discharge pressure (>= 0). A running pump has a
        shortfall when the required head is above the chart's maximum head at the operating rate. A
        pump that is not running has its operational discharge pressure at the suction pressure, so
        the shortfall is the requested outlet pressure minus the suction pressure.
        """
        return max(0.0, self.requested_outlet_pressure_bara - self.operational_discharge_pressure_bara)


class Pump(LiquidProcessUnit):
    """A single-speed / variable-speed pump.

    Args:
        pump_chart: Chart data (rate/head/efficiency curves). A single curve gives a
            single-speed pump; multiple curves give a variable-speed pump.
        minimum_flow_rate_m3_per_hour: Required minimum flow [m3/h]. A fixed
            vertical line in the rate-head plane; the operating rate is recirculated up to it.
            Must be at least the chart's minimum rate. Defaults to the chart's minimum rate
            when not provided.
        process_unit_id: Identity used to reference the pump; generated when not provided.
    """

    def __init__(
        self,
        pump_chart: ChartData,
        minimum_flow_rate_m3_per_hour: float | None = None,
        process_unit_id: ProcessUnitId | None = None,
    ):
        self._id: Final[ProcessUnitId] = process_unit_id or Pump._create_id()
        self._pump_chart: Chart = Chart(pump_chart)
        self._validate_pump_chart_efficiency()
        if minimum_flow_rate_m3_per_hour is None:
            minimum_flow_rate_m3_per_hour = self._pump_chart.minimum_rate
        if minimum_flow_rate_m3_per_hour < self._pump_chart.minimum_rate:
            raise EcalcValidationException(
                f"Minimum flow rate ({minimum_flow_rate_m3_per_hour} m3/h) cannot be below the "
                f"chart's minimum rate ({self._pump_chart.minimum_rate} m3/h); the operating "
                f"point would fall outside the pump chart."
            )
        self._minimum_flow_rate_m3_per_hour = minimum_flow_rate_m3_per_hour
        self._speed_rpm: float | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def pump_chart(self) -> Chart:
        return self._pump_chart

    @property
    def minimum_flow_rate_m3_per_hour(self) -> float:
        """The pump's minimum flow [m3/h] - the fixed vertical line in the
        rate-head plane, for plotting the min-flow line on the chart."""
        return self._minimum_flow_rate_m3_per_hour

    def set_speed(self, speed_rpm: float | None) -> None:
        self._speed_rpm = speed_rpm

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        """The stream at the pump discharge, for the set speed and the rate of the inlet stream."""
        rate_m3_per_hour = inlet_stream.volumetric_rate_m3_per_hour
        if rate_m3_per_hour <= 0:
            return inlet_stream
        if self._speed_rpm is None:
            raise ValueError("Speed not set. A running pump needs a speed.")
        head_joule_per_kg = self._head_at_rate_and_speed(rate_m3_per_hour=rate_m3_per_hour, speed_rpm=self._speed_rpm)
        return inlet_stream.with_pressure(
            inlet_stream.pressure_bara + Unit.PASCAL.to(Unit.BARA)(head_joule_per_kg * inlet_stream.density_kg_per_m3)
        )

    def evaluate(self, inlet_stream: LiquidStream, requested_outlet_pressure_bara: float) -> PumpEvaluationResult:
        """Evaluate the pump for an inlet liquid stream and a requested outlet pressure.

        A required head above the chart's maximum head, or a rate above the chart's maximum rate,
        gives a power value and is flagged via ``failure_status``. A non-positive rate means the pump
        is not running: power and operational head are zero, the operational discharge pressure
        equals the suction pressure, and the result is valid.
        """
        self._validate_requested_outlet_pressure(requested_outlet_pressure_bara)

        density = inlet_stream.density_kg_per_m3
        rate_m3_per_hour = inlet_stream.volumetric_rate_m3_per_hour

        required_head = self._calculate_head(
            suction_pressure=inlet_stream.pressure_bara,
            outlet_pressure=requested_outlet_pressure_bara,
            density=density,
        )

        if rate_m3_per_hour <= 0:
            # Pump not running: no head, so the operational discharge pressure equals the suction
            # pressure. The required head is the head the requested outlet pressure would need from
            # a running pump.
            return PumpEvaluationResult(
                inlet_stream=inlet_stream,
                shaft_power_mw=0.0,
                efficiency=None,
                specific_shaft_work_joule_per_kg=None,
                required_head_joule_per_kg=required_head,
                operational_head_joule_per_kg=0.0,
                operational_volumetric_rate_m3_per_hour=0.0,
                recirculation_rate_m3_per_hour=0.0,
                requested_outlet_pressure_bara=requested_outlet_pressure_bara,
                operational_discharge_pressure_bara=inlet_stream.pressure_bara,
                speed_rpm=None,
                failure_status=PumpFailureStatus.NO_FAILURE,
                process_unit_id=self._id,
            )

        # Recirculation (internal): clamp the operating rate up to the largest binding minimum
        # flow - the user-defined vertical line and the chart's minimum-flow line at the required
        # head (which collapses to the chart minimum rate for a single-speed chart).
        chart_minimum_flow_at_head = float(self._pump_chart.minimum_rate_as_function_of_head(required_head))
        operating_rate_m3_per_hour = max(
            rate_m3_per_hour,
            self._minimum_flow_rate_m3_per_hour,
            chart_minimum_flow_at_head,
        )

        minimum_head_at_rate = float(self._pump_chart.minimum_head_as_function_of_rate(operating_rate_m3_per_hour))
        maximum_head_at_rate = float(self._pump_chart.maximum_head_as_function_of_rate(operating_rate_m3_per_hour))

        # The pump runs between the chart's minimum and maximum head at the operating rate. Below the
        # minimum, a downstream choke drops the difference (``choke_pressure_drop_bara``); above the
        # maximum, the pump falls short of the requested outlet pressure (``pressure_shortfall_bara``).
        operational_head = min(max(required_head, minimum_head_at_rate), maximum_head_at_rate)

        efficiency = self._efficiency(
            rate_m3_per_hour=operating_rate_m3_per_hour,
            head_joule_per_kg=operational_head,
        )
        speed_rpm = self._speed_at_operating_point(
            rate_m3_per_hour=operating_rate_m3_per_hour,
            head_joule_per_kg=operational_head,
        )
        specific_shaft_work = operational_head / efficiency
        operating_mass_rate_kg_per_h = operating_rate_m3_per_hour * density
        shaft_power_mw = operating_mass_rate_kg_per_h * specific_shaft_work / 3600.0 / 1_000_000.0
        operational_discharge_pressure_bara = inlet_stream.pressure_bara + Unit.PASCAL.to(Unit.BARA)(
            operational_head * density
        )

        return PumpEvaluationResult(
            inlet_stream=inlet_stream,
            shaft_power_mw=shaft_power_mw,
            efficiency=efficiency,
            specific_shaft_work_joule_per_kg=specific_shaft_work,
            required_head_joule_per_kg=required_head,
            operational_head_joule_per_kg=operational_head,
            operational_volumetric_rate_m3_per_hour=operating_rate_m3_per_hour,
            recirculation_rate_m3_per_hour=operating_rate_m3_per_hour - rate_m3_per_hour,
            requested_outlet_pressure_bara=requested_outlet_pressure_bara,
            operational_discharge_pressure_bara=operational_discharge_pressure_bara,
            speed_rpm=speed_rpm,
            failure_status=self._determine_failure_status(
                head_joule_per_kg=required_head,
                maximum_head_at_rate=maximum_head_at_rate,
                rate_m3_per_hour=operating_rate_m3_per_hour,
            ),
            process_unit_id=self._id,
        )

    def get_max_volumetric_rate_m3_per_day(
        self, suction_pressure: float, outlet_pressure: float, density: float
    ) -> float:
        """Maximum volumetric rate [m3/day] the pump can deliver at the given pressures and density."""
        head = self._calculate_head(suction_pressure=suction_pressure, outlet_pressure=outlet_pressure, density=density)
        return float(self._pump_chart.maximum_rate_as_function_of_head(head) * UnitConstants.HOURS_PER_DAY)

    @staticmethod
    def _validate_requested_outlet_pressure(requested_outlet_pressure_bara: float) -> None:
        if requested_outlet_pressure_bara <= 0:
            raise NonPositivePressureException(requested_outlet_pressure_bara)

    @staticmethod
    def _calculate_head(suction_pressure: float, outlet_pressure: float, density: float) -> float:
        """Head in joule per kg [J/kg]."""
        return Unit.BARA.to(Unit.PASCAL)(outlet_pressure - suction_pressure) / density

    def _efficiency(self, rate_m3_per_hour: float, head_joule_per_kg: float) -> float:
        if self._pump_chart.is_100_percent_efficient:
            return 1.0
        return float(
            self._pump_chart.efficiency_as_function_of_rate_and_head(
                rates=np.asarray([rate_m3_per_hour]),
                heads=np.asarray([head_joule_per_kg]),
            )[0]
        )

    def _speed_at_operating_point(self, rate_m3_per_hour: float, head_joule_per_kg: float) -> float:
        """Speed [rpm] at a rate and a head: linear in head between the two curves that bracket the head at
        that rate. The inverse of ``_head_at_rate_and_speed``."""
        speeds, heads = self._speeds_and_heads_at_rate(rate_m3_per_hour)
        return float(np.interp(head_joule_per_kg, heads, speeds))

    def _head_at_rate_and_speed(self, rate_m3_per_hour: float, speed_rpm: float) -> float:
        """Head [J/kg] at a rate and a speed: linear in speed between the two curves that bracket the speed,
        each read at that rate. The inverse of ``_speed_at_operating_point``."""
        speeds, heads = self._speeds_and_heads_at_rate(rate_m3_per_hour)
        return float(np.interp(speed_rpm, speeds, heads))

    def _speeds_and_heads_at_rate(self, rate_m3_per_hour: float) -> tuple[list[float], list[float]]:
        """The speed [rpm] of each curve and its head [J/kg] at the rate, by increasing speed."""
        curves = sorted(self._pump_chart.curves, key=lambda curve: curve.speed_rpm)
        return (
            [float(curve.speed_rpm) for curve in curves],
            [float(curve.head_as_function_of_rate(rate_m3_per_hour)) for curve in curves],
        )

    def _determine_failure_status(
        self,
        head_joule_per_kg: float,
        maximum_head_at_rate: float,
        rate_m3_per_hour: float,
    ) -> PumpFailureStatus:
        above_maximum_head = head_joule_per_kg > maximum_head_at_rate
        above_maximum_rate = rate_m3_per_hour > float(self._pump_chart.maximum_rate)

        if above_maximum_head and above_maximum_rate:
            return PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE
        if above_maximum_head:
            return PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE
        if above_maximum_rate:
            return PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE
        return PumpFailureStatus.NO_FAILURE

    def _validate_pump_chart_efficiency(self) -> None:
        if any(efficiency <= 0 for curve in self._pump_chart.curves for efficiency in curve.efficiency):
            raise EcalcValidationException("Pump efficiency must be greater than zero.")
