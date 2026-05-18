"""Regenerate the regression snapshot from the current NeqSim jar.

Invoked via ``pytest --regenerate-neqsim-snapshot`` (see the
``pytest_addoption`` hook in ``compatibility/conftest.py``). Not
intended to be called directly.
"""

from __future__ import annotations

import json
from pathlib import Path

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS
from ._spec import SNAPSHOT_PROPERTIES, iter_states, state_key

SNAPSHOT_PATH = Path(__file__).with_name("reference_snapshot.json")


def regenerate() -> Path:
    """Walk the spec, build a NeqsimFluid for every state, write the
    JSON snapshot, and return the path."""
    from ecalc_neqsim_wrapper import NeqsimService

    with NeqsimService.factory(use_jpype=False).initialize():
        snapshot: dict[str, dict[str, float]] = {}
        for composition_name, pressure_bara, temperature_kelvin, eos_model in iter_states():
            fluid = NeqsimFluid.create_thermo_system(
                composition=COMPOSITIONS[composition_name],
                pressure_bara=pressure_bara,
                temperature_kelvin=temperature_kelvin,
                eos_model=eos_model,
            )
            key = state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)
            snapshot[key] = {prop: float(getattr(fluid, prop)) for prop in SNAPSHOT_PROPERTIES}

    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    return SNAPSHOT_PATH
