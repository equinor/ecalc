from collections.abc import Sequence

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.mappers.process.process_partitioner import MappedSection
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.mixer import Mixer
from libecalc.process.process_units.splitter import Splitter

_CHOKE = ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE")

_PRESSURE_CONTROL_REQUIRES_ANTI_SURGE = {
    "COMMON_ASV": AntiSurgeType.COMMON_ASV,
    "INDIVIDUAL_ASV_RATE": AntiSurgeType.INDIVIDUAL_ASV,
    "INDIVIDUAL_ASV_PRESSURE": AntiSurgeType.INDIVIDUAL_ASV,
}


class MappedSectionValidator:
    """Validates section strategies and unit composition. Operates on process sections only."""

    def validate(self, sections: Sequence[MappedSection]) -> None:
        for s in sections:
            self._validate_strategy_compatibility(s)
            self._validate_anti_surge_vs_compressors(s)
            self._validate_pressure_control_vs_compressors(s)
            self._validate_common_asv_units(s)

    @staticmethod
    def _validate_strategy_compatibility(s: MappedSection) -> None:
        required = _PRESSURE_CONTROL_REQUIRES_ANTI_SURGE.get(s.constraint.pressure_control)
        if required and s.constraint.anti_surge != required:
            raise EcalcValidationException(
                f"PRESSURE_CONTROL '{s.constraint.pressure_control}' requires ANTI_SURGE '{required}', got '{s.constraint.anti_surge}'"
            )

    def _validate_anti_surge_vs_compressors(self, s: MappedSection) -> None:
        location = self._section_location(s)
        has_compressors = any(isinstance(u, Compressor) for u in s.process_units)
        if has_compressors and s.constraint.anti_surge is AntiSurgeType.NO_ASV:
            raise EcalcValidationException(
                f"'{s.constraint.anti_surge}' cannot be used for {location}. Sections with compressors must use "
                f" COMMON_ASV or INDIVIDUAL_ASV anti-surge."
            )
        if not has_compressors and s.constraint.anti_surge is not AntiSurgeType.NO_ASV:
            raise EcalcValidationException(
                f"'{s.constraint.anti_surge}' cannot be used for {location}. Sections without cannot have anti-surge."
            )

    def _validate_pressure_control_vs_compressors(self, s: MappedSection) -> None:
        location = self._section_location(s)
        has_compressors = any(isinstance(u, Compressor) for u in s.process_units)
        if not has_compressors and s.constraint.pressure_control not in _CHOKE:
            raise EcalcValidationException(
                f"'{s.constraint.pressure_control}' cannot be used for {location} because the section does not contain a compressor."
                f"Sections without compressors must use UPSTREAM_CHOKE or DOWNSTREAM_CHOKE."
            )

    def _validate_common_asv_units(self, s: MappedSection) -> None:
        location = self._section_location(s)
        if s.constraint.anti_surge == "COMMON_ASV" and any(isinstance(u, (Mixer, Splitter)) for u in s.process_units):
            raise EcalcValidationException(
                f"COMMON_ASV cannot be used for {location} because the section contains a mixer or splitter."
            )

    @staticmethod
    def _section_location(section: MappedSection) -> str:
        if section.constraint.process_unit is not None:
            return f"constraint at process unit '{section.constraint.process_unit}'"
        return "constraint at pipeline outlet"
