"""A single-speed / variable-speed pump for an incompressible liquid.

The pump raises an inlet liquid stream toward a required (target) discharge pressure. The head
follows directly from the pressure rise and the density (``head = (p_d - p_s) / rho``), and the
pump chart supplies the efficiency and the feasible operating window. Everything is closed-form:
the operating point is read off the chart envelope, so there is no solver and no iteration.

When the pump cannot sit exactly on the target, the head is bounded to the chart envelope in both
directions:

- Below the envelope - a single-speed pump is pinned to its curve, and a variable-speed pump
  cannot deliver less head than its minimum-speed curve - it delivers a higher (operating) head
  than required. The excess would be dropped by a downstream choke (``choke_pressure_drop_bara``).
- Above the envelope - neither pump type can deliver more head than its maximum-speed curve - the
  operating head is capped there, so the delivered discharge pressure falls short of what was
  required (``pressure_shortfall_bara``). ``failure_status`` is derived from the required head, so
  it reports the infeasibility independently of the cap.

The result exposes both the required and the operating discharge pressure so a caller can tell
these regimes apart. The rate itself is never capped - only the head is. A rate above the chart's
own maximum rate is flagged separately, via ``PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE``. At such
a rate, the head cap itself is also less reliable: ``Chart.maximum_head_as_function_of_rate``
does not extrapolate the curve's declining trend past its highest measured rate - it holds the head
flat at the value from that highest-rate point instead. For example, if the curve's highest-rate
point is 927 m3/h, evaluating the pump at 1200 m3/h uses that same 927 m3/h head value as the cap.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

import numpy as np

from libecalc.common.ddd import value_object
from libecalc.common.ddd.entity import Entity
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.units import Unit, UnitConstants
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.liquid_stream_propagator import LiquidStreamPropagator


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
        required_head_joule_per_kg: Head implied by the suction and required discharge pressures,
            ``(p_d - p_s) / rho`` [J/kg].
        operational_head_joule_per_kg: Actual head the pump operates at [J/kg], bounded to the
            chart envelope. Exceeds the required head when the pump cannot deliver less head than
            its minimum-speed curve at the operating rate; falls below it when the required head
            exceeds the maximum-speed curve; otherwise equals the required head.
        operational_volumetric_rate_m3_per_hour: Volumetric rate the pump operates at
            [m3/h], i.e. the requested rate raised to the minimum flow when recirculating.
        recirculation_rate_m3_per_hour: Internal recirculation [m3/h] to maintain the minimum flow
            = operational rate minus requested rate; zero when not recirculating.
        required_discharge_pressure_bara: Discharge pressure the pump was asked to deliver [bara].
        operational_discharge_pressure_bara: Discharge pressure the pump actually delivers [bara],
            from the operational head. Exceeds the required discharge pressure when the pump
            over-delivers head (see ``choke_pressure_drop_bara``); falls short of it when the
            required head is above the chart's capacity at the operating rate (see
            ``pressure_shortfall_bara``).
        speed_rpm: Operating speed [rpm] of the pump (the speed curve through the operating point);
            the single curve's speed for a single-speed pump, ``None`` when not running.
        failure_status: Feasibility outcome; ``NO_FAILURE`` when within the chart envelope.
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
    required_discharge_pressure_bara: float
    operational_discharge_pressure_bara: float
    speed_rpm: float | None
    failure_status: PumpFailureStatus
    process_unit_id: ProcessUnitId

    @property
    def is_valid(self) -> bool:
        return self.failure_status == PumpFailureStatus.NO_FAILURE

    @property
    def choke_pressure_drop_bara(self) -> float:
        """Pressure a downstream choke would drop to reach the required discharge pressure [bara].

        The excess the pump over-delivers = operational minus required discharge pressure (>= 0).
        """
        return max(0.0, self.operational_discharge_pressure_bara - self.required_discharge_pressure_bara)

    @property
    def pressure_shortfall_bara(self) -> float:
        """Pressure the pump falls short of the required discharge pressure [bara].

        Non-zero only when the duty is above the pump's capacity at the operating rate: the head is
        bounded by the chart's maximum-speed curve, so the delivered pressure is lower than required.
        """
        return max(0.0, self.required_discharge_pressure_bara - self.operational_discharge_pressure_bara)


class Pump(Entity[ProcessUnitId], LiquidStreamPropagator):
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
        self._discharge_pressure_bara: float | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    @classmethod
    def _create_id(cls) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())

    @property
    def pump_chart(self) -> Chart:
        return self._pump_chart

    @property
    def minimum_flow_rate_m3_per_hour(self) -> float:
        """The pump's minimum flow [m3/h] - the fixed vertical line in the
        rate-head plane, for plotting the min-flow line on the chart."""
        return self._minimum_flow_rate_m3_per_hour

    def set_discharge_pressure(self, discharge_pressure_bara: float) -> None:
        """Set the required (target) discharge pressure used by ``propagate_stream``."""
        self._validate_discharge_pressure(discharge_pressure_bara)
        self._discharge_pressure_bara = discharge_pressure_bara

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        """Propagate the inlet stream to the pump's delivered outlet stream.

        The delivered stream is at the requested rate - recirculation is internal - at the
        operational discharge pressure. For the full evaluation (power, heads, speed, feasibility),
        call ``evaluate``; it is closed-form and deterministic, so it reproduces this outlet exactly.
        """
        if self._discharge_pressure_bara is None:
            raise ValueError("Discharge pressure not set. Call set_discharge_pressure first.")
        result = self.evaluate(inlet_stream, self._discharge_pressure_bara)
        return inlet_stream.with_pressure(result.operational_discharge_pressure_bara)

    def evaluate(self, inlet_stream: LiquidStream, discharge_pressure_bara: float) -> PumpEvaluationResult:
        """Evaluate the pump for a given inlet liquid stream and required discharge pressure.

        Points that fall outside the chart envelope still produce a power value but are flagged via
        ``failure_status``. A non-positive rate means the pump is not running: power and heads are
        zero and the result is valid.
        """
        self._validate_discharge_pressure(discharge_pressure_bara)

        density = inlet_stream.density_kg_per_m3
        rate_m3_per_hour = inlet_stream.volumetric_rate_m3_per_hour

        required_head = self._calculate_head(
            suction_pressure=inlet_stream.pressure_bara,
            discharge_pressure=discharge_pressure_bara,
            density=density,
        )

        if rate_m3_per_hour <= 0:
            # Pump not running: no head produced, so the operational discharge equals the suction
            # pressure. The required side still reflects the requested duty.
            return PumpEvaluationResult(
                inlet_stream=inlet_stream,
                shaft_power_mw=0.0,
                efficiency=None,
                specific_shaft_work_joule_per_kg=None,
                required_head_joule_per_kg=required_head,
                operational_head_joule_per_kg=0.0,
                operational_volumetric_rate_m3_per_hour=0.0,
                recirculation_rate_m3_per_hour=0.0,
                required_discharge_pressure_bara=discharge_pressure_bara,
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

        # The pump cannot deliver less head than its (minimum-speed) curve, nor more than its
        # (maximum-speed) curve. Below the curve the surplus is dropped by a downstream choke; above it
        # the pump simply falls short of the duty - see ``pressure_shortfall_bara``.
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
            required_discharge_pressure_bara=discharge_pressure_bara,
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
        self, suction_pressure: float, discharge_pressure: float, density: float
    ) -> float:
        """Maximum volumetric rate [m3/day] the pump can deliver at the given pressures and density."""
        head = self._calculate_head(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, density=density
        )
        return float(self._pump_chart.maximum_rate_as_function_of_head(head) * UnitConstants.HOURS_PER_DAY)

    @staticmethod
    def _validate_discharge_pressure(discharge_pressure_bara: float) -> None:
        if discharge_pressure_bara <= 0:
            raise NonPositivePressureException(discharge_pressure_bara)

    @staticmethod
    def _calculate_head(suction_pressure: float, discharge_pressure: float, density: float) -> float:
        """Head in joule per kg [J/kg]."""
        return Unit.BARA.to(Unit.PASCAL)(discharge_pressure - suction_pressure) / density

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
        curves = sorted(self._pump_chart.curves, key=lambda curve: curve.speed_rpm)
        if len(curves) == 1:
            return float(curves[0].speed_rpm)

        speeds = [float(curve.speed_rpm) for curve in curves]
        heads = [float(curve.head_as_function_of_rate(rate_m3_per_hour)) for curve in curves]
        if head_joule_per_kg <= heads[0]:
            return speeds[0]
        if head_joule_per_kg >= heads[-1]:
            return speeds[-1]
        for index in range(len(curves) - 1):
            head_low, head_high = heads[index], heads[index + 1]
            if head_low <= head_joule_per_kg <= head_high:
                fraction = (head_joule_per_kg - head_low) / (head_high - head_low) if head_high != head_low else 0.0
                return speeds[index] + fraction * (speeds[index + 1] - speeds[index])
        return speeds[-1]

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
