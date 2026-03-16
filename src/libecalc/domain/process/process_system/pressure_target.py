from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureTarget(ProcessUnit):
    """A marker unit that declares a required pressure at a point in a sequence of process units.

    Placed between process units in a flat process_items list, a PressureTarget
    signals that the solver must deliver the specified outlet pressure at this position
    before continuing with the remaining process units.

    propagate_stream() does not modify the stream. Its sole purpose is to carry
    the target pressure and, optionally, a pressure-control mode to be applied
    by the process units that follow it.
    """

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        target_pressure_bara: float,
        downstream_pressure_control: FixedSpeedPressureControl | None = None,
    ) -> None:
        self._id = process_unit_id
        self._target_pressure_bara = target_pressure_bara
        self._downstream_pressure_control = downstream_pressure_control

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def target_pressure_bara(self) -> float:
        return self._target_pressure_bara

    @property
    def has_target_pressure(self) -> bool:
        return True

    @property
    def downstream_pressure_control(self) -> FixedSpeedPressureControl | None:
        return self._downstream_pressure_control

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return inlet_stream
