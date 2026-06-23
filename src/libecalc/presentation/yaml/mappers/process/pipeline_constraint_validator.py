from collections.abc import Sequence

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.mappers.process.pipeline_section_partitioner import PipelineConstraintSection
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.mixer import Mixer
from libecalc.process.process_units.splitter import Splitter

_ANTI_SURGE = ("COMMON_ASV", "INDIVIDUAL_ASV")
_CHOKE = ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE")

_PRESSURE_CONTROL_REQUIRES_ANTI_SURGE = {
    "COMMON_ASV": "COMMON_ASV",
    "INDIVIDUAL_ASV_RATE": "INDIVIDUAL_ASV",
    "INDIVIDUAL_ASV_PRESSURE": "INDIVIDUAL_ASV",
}


class PipelineConstraintValidator:
    """Validates section strategies and unit composition. Operates on pipeline constraint sections only."""

    def validate(self, sections: Sequence[PipelineConstraintSection]) -> None:
        for s in sections:
            self._validate_strategy_compatibility(s)
            self._validate_anti_surge_vs_compressors(s)
            self._validate_pressure_control_vs_compressors(s)
            self._validate_common_asv_units(s)

    @staticmethod
    def _validate_strategy_compatibility(s: PipelineConstraintSection) -> None:
        required = _PRESSURE_CONTROL_REQUIRES_ANTI_SURGE.get(s.pressure_control)
        if required and s.anti_surge != required:
            raise EcalcValidationException(
                f"PRESSURE_CONTROL '{s.pressure_control}' requires ANTI_SURGE '{required}', got '{s.anti_surge}'"
            )

    @staticmethod
    def _validate_anti_surge_vs_compressors(s: PipelineConstraintSection) -> None:
        has_compressors = any(isinstance(u, Compressor) for u in s.units)
        if has_compressors and s.anti_surge not in _ANTI_SURGE:
            raise EcalcValidationException(
                f"Section {s.index} with compressors must use COMMON_ASV or INDIVIDUAL_ASV, got '{s.anti_surge}'."
            )
        if not has_compressors and s.anti_surge is not None:
            raise EcalcValidationException(
                f"Section {s.index} without compressors cannot have anti-surge, got '{s.anti_surge}'."
            )

    @staticmethod
    def _validate_pressure_control_vs_compressors(s: PipelineConstraintSection) -> None:
        has_compressors = any(isinstance(u, Compressor) for u in s.units)
        if not has_compressors and s.pressure_control not in _CHOKE:
            raise EcalcValidationException(
                f"Section {s.index} without compressors must use UPSTREAM_CHOKE or DOWNSTREAM_CHOKE, "
                f"got '{s.pressure_control}'."
            )

    @staticmethod
    def _validate_common_asv_units(s: PipelineConstraintSection) -> None:
        if s.anti_surge == "COMMON_ASV" and any(isinstance(u, (Mixer, Splitter)) for u in s.units):
            raise EcalcValidationException(f"Section {s.index}: COMMON_ASV cannot contain a mixer or splitter.")
