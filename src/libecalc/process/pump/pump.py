"""A single-point pump for an incompressible liquid.

The pump raises an inlet liquid stream to a set discharge pressure. As the liquid is
incompressible, the outlet stream is the inlet at the discharge pressure (density and rate
unchanged).
"""

from __future__ import annotations

from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import SimplifiedLiquidStream


class Pump(ProcessUnit[SimplifiedLiquidStream]):
    """A single-point pump that raises a liquid stream to a set discharge pressure.

    Args:
        process_unit_id: Identity used to reference the pump; generated when not provided.
    """

    def __init__(self, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._discharge_pressure_bara: float | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_discharge_pressure(self, discharge_pressure_bara: float) -> None:
        if discharge_pressure_bara <= 0:
            raise NonPositivePressureException(discharge_pressure_bara)
        self._discharge_pressure_bara = discharge_pressure_bara

    def propagate_stream(self, inlet_stream: SimplifiedLiquidStream) -> SimplifiedLiquidStream:
        if self._discharge_pressure_bara is None:
            raise ValueError("Discharge pressure not set. Call set_discharge_pressure first.")
        return inlet_stream.with_pressure(self._discharge_pressure_bara)
