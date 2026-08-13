"""Structural guard for wet-composition temperature floors."""

from __future__ import annotations

import pytest

from ..behaviour.test_flash_operations import _PH_PROBE_CASES
from ..behaviour.test_phase_operations import _PHASE_EXTRACTION_CASES
from ..compositions import COMPOSITIONS, min_temperature_kelvin_for
from ..regression._spec import iter_states
from .test_sanity import _ALL_CASES as _SANITY_ALL_CASES


def _wet_names() -> list[str]:
    return [name for name, composition in COMPOSITIONS.items() if getattr(composition, "water", 0.0) > 0.0]


@pytest.mark.parametrize("composition_name", _wet_names())
def test_wet_composition_has_registered_floor(composition_name: str) -> None:
    """Every wet composition must have a registered minimum temperature."""
    assert min_temperature_kelvin_for(composition_name) > float("-inf"), (
        f"{composition_name} contains water but has no entry in MIN_TEMPERATURE_KELVIN_PER_COMPOSITION"
    )


def _violations_from_cases(cases, *, pressure_index: int = 2, temperature_index: int = 3) -> list[str]:
    """Each entry is a `pytest.param(...)` with values
    `(name, composition, pressure_bara, temperature_kelvin, [eos])`."""
    violations: list[str] = []
    for case in cases:
        name = case.values[0]
        pressure_bara = case.values[pressure_index]
        temperature_kelvin = case.values[temperature_index]
        floor = min_temperature_kelvin_for(name)
        if temperature_kelvin < floor:
            violations.append(f"{name} at ({pressure_bara} bara, {temperature_kelvin} K), floor={floor} K")
    return violations


def test_sanity_cases_exclude_wet_below_floor() -> None:
    violations = _violations_from_cases(_SANITY_ALL_CASES)
    assert not violations, "sanity cases include wet × sub-floor:\n  " + "\n  ".join(violations)


def test_phase_operations_cases_exclude_wet_below_floor() -> None:
    violations = _violations_from_cases(_PHASE_EXTRACTION_CASES)
    assert not violations, "behaviour.test_phase_operations cases include wet × sub-floor:\n  " + "\n  ".join(
        violations
    )


def test_flash_probe_cases_exclude_wet_below_floor() -> None:
    violations = _violations_from_cases(_PH_PROBE_CASES, pressure_index=1, temperature_index=2)
    assert not violations, "behaviour.test_flash_operations cases include wet × sub-floor:\n  " + "\n  ".join(
        violations
    )


def test_reference_snapshot_iter_excludes_wet_below_floor() -> None:
    violations: list[str] = []
    for composition_name, pressure_bara, temperature_kelvin, _eos in iter_states():
        floor = min_temperature_kelvin_for(composition_name)
        if temperature_kelvin < floor:
            violations.append(f"{composition_name} at ({pressure_bara} bara, {temperature_kelvin} K), floor={floor} K")
    assert not violations, "regression.iter_states yielded wet × sub-floor states:\n  " + "\n  ".join(violations)
