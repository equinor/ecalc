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
from ._spec import (
    PH_FLASH_PRESSURE_RATIO,
    PH_SNAPSHOT_PROPERTIES,
    TP_SNAPSHOT_PROPERTIES,
    iter_states,
    ph_state_key,
    tp_state_key,
)

SNAPSHOT_PATH = Path(__file__).with_name("reference_snapshot.json")


def regenerate() -> Path:
    """Walk the spec, build a NeqsimFluid for every state, write the
    JSON snapshot, and return the path."""
    from ecalc_neqsim_wrapper import NeqsimService

    with NeqsimService.factory(use_jpype=False).initialize():
        snapshot: dict[str, dict[str, float]] = {}
        for composition_name, pressure_bara, temperature_kelvin, eos_model in iter_states():
            inlet = NeqsimFluid.create_thermo_system(
                composition=COMPOSITIONS[composition_name],
                pressure_bara=pressure_bara,
                temperature_kelvin=temperature_kelvin,
                eos_model=eos_model,
            )

            # TP-flash entry
            tp_key = tp_state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)
            snapshot[tp_key] = {prop: float(getattr(inlet, prop)) for prop in TP_SNAPSHOT_PROPERTIES}

            # PH-flash entry: isenthalpic compression to 1.5× inlet pressure
            outlet_pressure = pressure_bara * PH_FLASH_PRESSURE_RATIO
            outlet = inlet.set_new_pressure_and_enthalpy(
                new_pressure=outlet_pressure,
                new_enthalpy_joule_per_kg=inlet.enthalpy_joule_per_kg,
            )
            ph_key = ph_state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)
            snapshot[ph_key] = {prop: float(getattr(outlet, prop)) for prop in PH_SNAPSHOT_PROPERTIES}

    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    return SNAPSHOT_PATH
