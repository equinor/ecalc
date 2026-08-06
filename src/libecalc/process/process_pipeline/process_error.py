from dataclasses import dataclass

from libecalc.common.errors.exceptions import EcalcError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


@dataclass(frozen=True)
class CompressorOperatingPoint:
    """Context about the compressor state when a failure occurred."""

    inlet_pressure_bara: float
    inlet_temperature_kelvin: float
    actual_rate_m3_per_hour: float
    polytropic_head_joule_per_kg: float
    polytropic_efficiency: float
    speed: float


class ProcessError(EcalcError):
    def __init__(self, reason: str | None = None):
        self.reason = reason
        super().__init__(title="Unable to produce an outlet stream", message=reason or "")


class CompressorSurgeError(ProcessError):
    """Compressor inlet is below its surge line. Anti-surge recirculation may recover this."""

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        actual_rate: float | None = None,
        boundary_rate: float | None = None,
    ):
        self.actual_rate = actual_rate
        self.boundary_rate = boundary_rate
        self.process_unit_id = process_unit_id
        super().__init__(
            f"Compressor {process_unit_id} is below surge line"
            + (
                f": actual {actual_rate:.3f}, minimum {boundary_rate:.3f} m³/h."
                if actual_rate and boundary_rate
                else "."
            )
        )


class CompressorStonewallError(ProcessError):
    """Compressor inlet is above its stonewall limit."""

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        actual_rate: float | None = None,
        boundary_rate: float | None = None,
    ):
        self.actual_rate = actual_rate
        self.boundary_rate = boundary_rate
        self.process_unit_id = process_unit_id
        super().__init__(
            f"Compressor {process_unit_id} is above stonewall"
            + (
                f": actual {actual_rate:.3f}, maximum {boundary_rate:.3f} m³/h."
                if actual_rate and boundary_rate
                else "."
            )
        )


class LiquidAtInletError(ProcessError):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        vapor_fraction: float,
    ):
        self.process_unit_id = process_unit_id
        self.vapor_fraction = vapor_fraction
        super().__init__(f"Inlet stream contains liquid (vapor fraction: {vapor_fraction:.3f})")


class OfftakeExceedsInletError(ProcessError):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        available_rate: float,
        offtake_rate: float,
    ):
        self.process_unit_id = process_unit_id
        self.available_rate = available_rate
        self.offtake_rate = offtake_rate
        super().__init__(
            f"Inlet rate {available_rate:.3f} sm³/day is less than demanded rate {offtake_rate:.3f} sm³/day."
        )


class InsufficientInletPressureError(ProcessError):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        inlet_pressure_bara: float,
        required_delta_pressure_bara: float,
    ):
        self.process_unit_id = process_unit_id
        self.inlet_pressure_bara = inlet_pressure_bara
        self.required_delta_pressure_bara = required_delta_pressure_bara
        super().__init__(
            f"Inlet pressure {inlet_pressure_bara:.3f} bara is insufficient for required pressure drop "
            f"{required_delta_pressure_bara:.3f} bara."
        )


class OutletFluidNotAchievableError(ProcessError):
    """The compressor's EOS calculation could not produce a valid outlet stream.

    This occurs when the thermodynamic flash at the computed outlet conditions
    fails to converge, indicating a physically unachievable state.
    """

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        unachievable_operating_point: CompressorOperatingPoint,
        reason: str = "Outlet fluid state is not achievable.",
    ):
        self.process_unit_id = process_unit_id
        self.unachievable_operating_point = unachievable_operating_point
        super().__init__(reason)
