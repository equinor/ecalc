"""Strict snapshot regression test for vendored NeqSim outputs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS
from ._spec import (
    PROPERTY_TOLERANCES,
    SNAPSHOT_PROPERTIES,
    iter_states,
    state_key,
)

SNAPSHOT_PATH = Path(__file__).with_name("reference_snapshot.json")


def _load_snapshot() -> dict[str, dict[str, float]]:
    if not SNAPSHOT_PATH.exists():
        pytest.fail(
            f"Reference snapshot file not found: {SNAPSHOT_PATH}. "
            f"Generate it with: "
            f"uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot"
        )
    return json.loads(SNAPSHOT_PATH.read_text())


_SNAPSHOT = _load_snapshot()


_CASES = [
    pytest.param(
        composition_name,
        pressure_bara,
        temperature_kelvin,
        eos_model,
        id=state_key(composition_name, pressure_bara, temperature_kelvin, eos_model),
    )
    for composition_name, pressure_bara, temperature_kelvin, eos_model in iter_states()
]


def _compare(prop_name: str, current: float, expected: float) -> str | None:
    """Return None if values are within tolerance, else a human-readable diff."""
    tol = PROPERTY_TOLERANCES[prop_name]
    rel_tol = tol["rel_tol"]
    abs_tol = tol["abs_tol"]

    if not math.isfinite(current) or not math.isfinite(expected):
        if math.isnan(current) and math.isnan(expected):
            return None
        if current == expected:
            return None
        return f"{prop_name}: non-finite mismatch (current={current!r}, expected={expected!r})"

    if math.isclose(current, expected, rel_tol=rel_tol, abs_tol=abs_tol):
        return None

    delta = current - expected
    rel = abs(delta) / abs(expected) if expected != 0.0 else math.inf
    return (
        f"{prop_name}: drift outside tolerance. "
        f"current={current!r}, expected={expected!r}, "
        f"delta={delta:+.3e}, rel_drift={rel:.3e} "
        f"(rel_tol={rel_tol:g}, abs_tol={abs_tol:g})"
    )


@pytest.mark.parametrize("composition_name,pressure_bara,temperature_kelvin,eos_model", _CASES)
def test_state_matches_snapshot(composition_name, pressure_bara, temperature_kelvin, eos_model):
    """Every property at every snapshotted state must match the recorded
    value within the per-property tolerance defined in ``_spec``."""
    key = state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)
    if key not in _SNAPSHOT:
        pytest.fail(
            f"State {key!r} is in the spec but missing from the snapshot. "
            f"Regenerate with: "
            f"uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot"
        )
    expected = _SNAPSHOT[key]

    fluid = NeqsimFluid.create_thermo_system(
        composition=COMPOSITIONS[composition_name],
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        eos_model=eos_model,
    )

    diffs = []
    for prop_name in SNAPSHOT_PROPERTIES:
        if prop_name not in expected:
            diffs.append(f"{prop_name}: missing from snapshot for this state")
            continue
        diff = _compare(prop_name, float(getattr(fluid, prop_name)), float(expected[prop_name]))
        if diff is not None:
            diffs.append(diff)

    if diffs:
        details = "\n  ".join(diffs)
        pytest.fail(
            f"Reference snapshot drift at {key!r}:\n  {details}\n\n"
            f"If this drift is acceptable, regenerate the snapshot with: "
            f"uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot"
        )


def test_snapshot_has_no_extra_states():
    """The snapshot file must not contain states that are no longer in
    the spec — otherwise dead entries accumulate across spec changes."""
    expected_keys = {
        state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)
        for composition_name, pressure_bara, temperature_kelvin, eos_model in iter_states()
    }
    extra = sorted(set(_SNAPSHOT) - expected_keys)
    assert not extra, (
        f"Snapshot contains {len(extra)} state(s) no longer in the spec:\n  "
        + "\n  ".join(extra)
        + "\n\nRegenerate the snapshot to drop them: "
        "uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot"
    )
