from libecalc.common.units import UnitConstants
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class DirectMixer(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, mix_rate: float = 0):
        self._id = process_unit_id
        self._mix_rate = mix_rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        added_mass_kg_per_h = (
            self._mix_rate * inlet_stream.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
        )
        return inlet_stream.with_mass_rate(inlet_stream.mass_rate_kg_per_h + added_mass_kg_per_h)

    def get_mix_rate(self) -> float:
        return self._mix_rate

    def set_mix_rate(self, mix_rate: float):
        self._mix_rate = mix_rate
