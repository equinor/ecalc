from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class LiquidInlet(LiquidProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or LiquidProcessUnit._create_id()

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        return inlet_stream
