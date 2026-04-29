from typing import Final

from libecalc.common.units import UnitConstants
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.stream_protocol import MixableStream


class DirectSplitter:
    def __init__(self, process_unit_id: ProcessUnitId | None = None, split_rate: float = 0):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnitId(ecalc_id_generator())
        self._split_rate = split_rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: MixableStream) -> MixableStream:
        removed_mass_kg_per_h = self._split_rate * inlet_stream.standard_density / UnitConstants.HOURS_PER_DAY
        return inlet_stream.with_mass_rate(inlet_stream.mass_rate_kg_per_h - removed_mass_kg_per_h)

    def set_split_rate(self, split_rate: float):
        self._split_rate = split_rate
