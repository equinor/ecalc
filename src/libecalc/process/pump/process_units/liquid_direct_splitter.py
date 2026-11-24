from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class LiquidDirectSplitter(LiquidProcessUnit):
    def __init__(self, split_rate_m3_per_hour: float = 0.0, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or LiquidProcessUnit._create_id()
        self._split_rate_m3_per_hour = split_rate_m3_per_hour

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_split_rate_m3_per_hour(self, split_rate_m3_per_hour: float) -> None:
        self._split_rate_m3_per_hour = split_rate_m3_per_hour

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        removed_mass_rate_kg_per_h = self._split_rate_m3_per_hour * inlet_stream.density_kg_per_m3
        return inlet_stream.with_mass_rate(inlet_stream.mass_rate_kg_per_h - removed_mass_rate_kg_per_h)
