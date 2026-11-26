from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class LiquidPressureDropper(LiquidProcessUnit):
    def __init__(self, pressure_drop_bara: float = 0.0, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or LiquidProcessUnit._create_id()
        self.set_pressure_drop_bara(pressure_drop_bara)

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def pressure_drop_bara(self) -> float:
        return self._pressure_drop_bara

    def set_pressure_drop_bara(self, pressure_drop_bara: float) -> None:
        if pressure_drop_bara < 0:
            raise ValueError("Pressure drop cannot be negative")
        self._pressure_drop_bara = pressure_drop_bara

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        """A stream with no rate passes unchanged: nothing flows, so no pressure is dropped."""
        if self._pressure_drop_bara == 0.0 or inlet_stream.volumetric_rate_m3_per_hour <= 0:
            return inlet_stream
        return inlet_stream.with_pressure(inlet_stream.pressure_bara - self._pressure_drop_bara)
