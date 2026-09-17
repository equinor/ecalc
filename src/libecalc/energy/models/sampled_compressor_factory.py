"""Builds the concrete SampledCompressor implementation for a sampled-compressor raw
sample table: derives SampledCompressorData (see the sibling sampled_compressor_data
module) and dispatches to the matching 1D, 2D, or 3D leaf class from
libecalc.energy.models.sampled_compressor for whichever of rate/suction_pressure/
discharge_pressure are active.
"""

from __future__ import annotations

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.models.sampled_compressor import (
    SampledCompressor,
    SampledCompressorBase,
    _DischargePressureCompressor1D,
    _PsPdCompressor2D,
    _RateCompressor1D,
    _RatePdCompressor2D,
    _RatePsCompressor2D,
    _SampledCompressor3D,
    _SuctionPressureCompressor1D,
)
from libecalc.energy.models.sampled_compressor_data import SampledCompressorData, VariableName

_SAMPLED_COMPRESSOR_LEAF_CLASSES: tuple[type[SampledCompressorBase], ...] = (
    _RateCompressor1D,
    _SuctionPressureCompressor1D,
    _DischargePressureCompressor1D,
    _RatePdCompressor2D,
    _RatePsCompressor2D,
    _PsPdCompressor2D,
    _SampledCompressor3D,
)

# Derived from each leaf class's own _active_variables, rather than maintained
# as a separate, hand-written table - so the dispatch rule and each class's contract
# can never drift apart.
_MODEL_CLASS_BY_ACTIVE_VARIABLES: dict[tuple[VariableName, ...], type[SampledCompressorBase]] = {
    leaf_cls._active_variables: leaf_cls for leaf_cls in _SAMPLED_COMPRESSOR_LEAF_CLASSES
}
if len(_MODEL_CLASS_BY_ACTIVE_VARIABLES) != len(_SAMPLED_COMPRESSOR_LEAF_CLASSES):
    raise AssertionError(
        "Two or more leaf classes declare the same _active_variables - the dict "
        "comprehension above would silently drop one of them from dispatch."
    )


class SampledCompressorFactory:
    """Builds the concrete SampledCompressor implementation - 1D, one of the three 2D
    variable-pair combinations, or 3D - appropriate for which of rate/suction_pressure/
    discharge_pressure are provided and non-degenerate (i.e. actually vary across the
    sample table)."""

    @staticmethod
    def create(
        energy_usage_values: list[float],
        rate_values: list[float] | None = None,
        suction_pressure_values: list[float] | None = None,
        discharge_pressure_values: list[float] | None = None,
        power_interpolation_values: list[float] | None = None,
    ) -> SampledCompressor:
        table = SampledCompressorData.from_raw_lists(
            energy_usage_values,
            rate_values,
            suction_pressure_values,
            discharge_pressure_values,
            power_interpolation_values,
        )
        try:
            model_cls = _MODEL_CLASS_BY_ACTIVE_VARIABLES[table.active_variables]
        except KeyError:
            raise IllegalStateException(
                f"Unsupported combination of active variables: {table.active_variables}"
            ) from None
        return model_cls(table)


__all__ = [
    "SampledCompressorFactory",
]
