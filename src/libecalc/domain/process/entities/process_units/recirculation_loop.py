from collections.abc import Sequence

from libecalc.common.units import UnitConstants
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter import Splitter
from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class DirectMixer(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, mix_rate: float):
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


class DirectSplitter(ProcessUnit):
    def __init__(self, process_unit_id: ProcessUnitId, split_rate: float):
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


class RecirculationLoop(ProcessSystem):
    def __init__(
        self,
        process_system_id: ProcessSystemId,
        inner_process: ProcessSystem | ProcessUnit,
        recirculation_rate: float = 0,
    ):
        self._id = process_system_id
        self._inner_process = inner_process
        self._validate_inner_process()
        self._mixer = DirectMixer(
            process_unit_id=create_process_unit_id(),
            mix_rate=recirculation_rate,
        )
        self._splitter = DirectSplitter(
            process_unit_id=create_process_unit_id(),
            split_rate=recirculation_rate,
        )

    def _validate_inner_process(self):
        if not isinstance(self._inner_process, ProcessSystem | ProcessUnit):
            raise DomainValidationException(
                "Recirculation loop should contain a ProcessSystem with a compressor or a single compressor"
            )
        if isinstance(self._inner_process, ProcessSystem):
            for process_unit in self._inner_process.get_process_units():
                if isinstance(process_unit, Splitter | Mixer):
                    raise DomainValidationException("Recirculation loop cannot contain splitters or mixers")
        if isinstance(self._inner_process, ProcessUnit):
            if not isinstance(self._inner_process, Compressor):
                raise DomainValidationException(
                    "Recirculation loop should contain a ProcessSystem with a compressor or a single compressor"
                )

    def get_id(self) -> ProcessSystemId:
        return self._id

    def get_process_units(self) -> Sequence[ProcessUnit | ProcessSystem]:
        if isinstance(self._inner_process, ProcessSystem):
            return [
                self._mixer,
                *self._inner_process.get_process_units(),
                self._splitter,
            ]
        else:
            return [
                self._mixer,
                self._inner_process,
                self._splitter,
            ]

    def get_process_systems(self) -> set[ProcessSystem]:
        process_systems = set()
        process_systems.add(self._inner_process)
        process_systems.update(self._inner_process.get_process_systems())

        return process_systems

    def get_process_system_unit_pairs(self) -> dict[ProcessUnitId | ProcessSystemId, ProcessSystemId]:
        process_system_unit_pairs = {}
        process_system_unit_pairs[self._inner_process.get_id()] = self.get_id()
        process_system_unit_pairs.update(self._inner_process.get_process_system_unit_pairs())

        return process_system_unit_pairs

    def set_recirculation_rate(self, rate: float):
        self._mixer.set_mix_rate(rate)
        self._splitter.set_split_rate(rate)

    def get_recirculation_rate(self) -> float:
        return self._mixer.get_mix_rate()

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        inner_inlet_stream = self._mixer.propagate_stream(inlet_stream=inlet_stream)

        inner_outlet_stream = self._inner_process.propagate_stream(inlet_stream=inner_inlet_stream)

        return self._splitter.propagate_stream(inlet_stream=inner_outlet_stream)
