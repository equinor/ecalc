from libecalc.common.units import UnitConstants
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class DirectSplitter(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, split_rate: float = 0):
        self._id = process_unit_id
        self._split_rate = split_rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        removed_mass_kg_per_h = (
            self._split_rate * inlet_stream.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
        )
        return inlet_stream.with_mass_rate(inlet_stream.mass_rate_kg_per_h - removed_mass_kg_per_h)

    def set_split_rate(self, split_rate: float):
        self._split_rate = split_rate
