from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class LiquidDirectMixer(LiquidProcessUnit):
    def __init__(self, mix_rate_m3_per_hour: float = 0.0, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or LiquidProcessUnit._create_id()
        self._mix_rate_m3_per_hour = mix_rate_m3_per_hour

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_mix_rate_m3_per_hour(self, mix_rate_m3_per_hour: float) -> None:
        self._mix_rate_m3_per_hour = mix_rate_m3_per_hour

    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream:
        added_mass_rate_kg_per_h = self._mix_rate_m3_per_hour * inlet_stream.density_kg_per_m3
        return inlet_stream.with_mass_rate(inlet_stream.mass_rate_kg_per_h + added_mass_rate_kg_per_h)
