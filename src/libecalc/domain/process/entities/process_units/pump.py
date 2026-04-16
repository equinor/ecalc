from libecalc.domain.process.process_pipeline.liquid_process_unit import LiquidProcessUnit
from libecalc.domain.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.value_objects.chart.chart import Chart, ChartData
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream

_BARA_TO_PASCAL = 1e5


class Pump(LiquidProcessUnit):
    """Pump stage operating on a liquid stream.

    Physics:
        head [J/kg]  = pressure_rise [Pa] / density [kg/m³]
        power [MW]   = density × head × Q [m³/s] / efficiency / 1e6

    For single-speed pumps the chart has one curve — no set_speed() needed.
    For variable-speed pumps, set_speed() must be called before propagate_stream().
    """

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        pump_chart: ChartData,
    ) -> None:
        self._id = process_unit_id
        self._pump_chart = Chart(pump_chart)
        self._speed: float | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_speed(self, speed: float) -> None:
        self._speed = speed

    @property
    def minimum_flow_rate(self) -> float:
        """Minimum volumetric flow rate [m³/h] at current speed."""
        return float(self._pump_chart.minimum_rate_as_function_of_speed(self.speed))

    @property
    def maximum_flow_rate(self) -> float:
        """Maximum volumetric flow rate [m³/h] at current speed."""
        return float(self._pump_chart.maximum_rate_as_function_of_speed(self.speed))

    def get_recirculation_range(self, inlet_stream: LiquidStream) -> Boundary:
        """How much recirculation (Sm³/day) is needed/available to stay within pump capacity.

        Standard ≈ actual for liquids; min/max rates [m³/h] × 24 → Sm³/day.
        """
        min_sm3_day = self.minimum_flow_rate * 24.0
        max_sm3_day = self.maximum_flow_rate * 24.0
        inlet_sm3_day = inlet_stream.standard_rate_sm3_per_day
        return Boundary(
            min=max(0.0, min_sm3_day - inlet_sm3_day),
            max=max(0.0, max_sm3_day - inlet_sm3_day),
        )

    @property
    def speed(self) -> float:
        if self._speed is None:
            if not self._pump_chart.is_variable_speed:
                return self._pump_chart.minimum_speed
            raise ValueError("Speed not set. Variable-speed Pump must be registered on a Shaft.")
        return self._speed

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        """Propagate liquid stream through the pump.

        Computes outlet pressure from hydraulic head and tracks shaft power.
        Raises RateTooLowError / RateTooHighError if the operating point is
        outside the pump chart envelope at the current speed.
        """
        rate = inlet_stream.volumetric_rate_m3_per_hour
        density = inlet_stream.density_kg_per_m3

        head, efficiency = self._head_and_efficiency_at_rate(rate)

        min_rate = float(self._pump_chart.minimum_rate_as_function_of_head(head))
        max_rate = float(self._pump_chart.maximum_rate_as_function_of_head(head))

        if rate < min_rate:
            raise RateTooLowError(
                actual_rate=rate,
                boundary_rate=min_rate,
                process_unit_id=self._id,
            )

        if rate > max_rate:
            raise RateTooHighError(
                actual_rate=rate,
                boundary_rate=max_rate,
                process_unit_id=self._id,
            )

        pressure_rise_bara = head * density / _BARA_TO_PASCAL
        outlet_pressure = inlet_stream.pressure_bara + pressure_rise_bara

        return inlet_stream.with_pressure(outlet_pressure)

    @property
    def minimum_speed(self) -> float:
        return self._pump_chart.minimum_speed

    @property
    def maximum_speed(self) -> float:
        return self._pump_chart.maximum_speed

    def _head_and_efficiency_at_rate(self, rate_m3_per_hour: float) -> tuple[float, float]:
        """Head [J/kg] and efficiency [-] at current speed and flow rate."""
        curve = self._pump_chart.get_curve_by_speed(self.speed)
        if curve is not None:
            return (
                float(curve.head_as_function_of_rate(rate_m3_per_hour)),
                float(curve.efficiency_as_function_of_rate(rate_m3_per_hour)),
            )

        # Variable speed between two curves — linear interpolation
        curves_below = [c for c in self._pump_chart.curves if c.speed <= self.speed]
        curves_above = [c for c in self._pump_chart.curves if c.speed >= self.speed]
        if not curves_below or not curves_above:
            raise ValueError(
                f"Speed {self.speed} rpm is outside the pump chart range "
                f"[{self._pump_chart.minimum_speed}, {self._pump_chart.maximum_speed}]."
            )

        c_low = curves_below[-1]
        c_high = curves_above[0]
        alpha = (self.speed - c_low.speed) / (c_high.speed - c_low.speed)

        head = (1 - alpha) * float(c_low.head_as_function_of_rate(rate_m3_per_hour)) + alpha * float(
            c_high.head_as_function_of_rate(rate_m3_per_hour)
        )
        efficiency = (1 - alpha) * float(c_low.efficiency_as_function_of_rate(rate_m3_per_hour)) + alpha * float(
            c_high.efficiency_as_function_of_rate(rate_m3_per_hour)
        )
        return head, efficiency
