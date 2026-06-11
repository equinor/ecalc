"""Spec shared by the snapshot generator and the snapshot test.

Single source of truth for which states are pinned at strict
per-property tolerances. Reads its envelope (P, T, EoS) from
``..envelope`` so a change to the operating envelope propagates
to the snapshot automatically.

Two snapshot tables are maintained:

* ``tp|...`` keys: TP-flash at each (P, T, EoS, composition) grid point.
  Pins the thermodynamic state that ecalc reads after inlet-stream creation.

* ``ph|...`` keys: PH-flash from the same inlet state to 1.5× the inlet
  pressure.  This is the core compressor step (isenthalpic compression),
  the operation most likely to drift silently across NeqSim jar bumps.
"""

from __future__ import annotations

from libecalc.process.fluid_stream.fluid_model import EoSModel

from ..compositions import is_state_supported
from ..envelope import (
    EOS_MODELS,
    high_pressure_grid,
    max_speed_probe_grid,
    nominal_grid,
)

# Focused snapshot subset spanning light, export, heavy, wet/dry, CO2-rich, and N2-heavy gases.
COMPOSITION_NAMES: tuple[str, ...] = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "c3_rich_wellstream",
    "c3_rich_wellstream_dry",
    "co2_heavy_injection",
    "n2_heavy",
)

# Main snapshot grid; wet compositions are filtered below their floor.
PRESSURE_TEMPERATURE_POINTS_BARA_KELVIN: tuple[tuple[float, float], ...] = (
    *nominal_grid(),
    *high_pressure_grid(),
    *max_speed_probe_grid(),
)

# Extra points for fragile flash regions.
EXTRA_POINTS_PER_COMPOSITION_BARA_KELVIN: dict[str, tuple[tuple[float, float], ...]] = {
    "c3_rich_wellstream_dry": (
        (100.0, 250.0),
        (200.0, 250.0),
    ),
}

# TP-flash: inlet-state properties ecalc reads directly.
TP_SNAPSHOT_PROPERTIES: tuple[str, ...] = (
    "z",
    "density",
    "kappa",
    "enthalpy_joule_per_kg",
    "vapor_fraction_molar",
    "molar_mass",
)

# PH-flash: outlet properties after isenthalpic compression to PH_FLASH_PRESSURE_RATIO × inlet P.
# kappa is excluded (not meaningful mid-stage); molar_mass is composition-invariant.
PH_SNAPSHOT_PROPERTIES: tuple[str, ...] = (
    "z",
    "density",
    "enthalpy_joule_per_kg",
    "temperature_kelvin",
    "vapor_fraction_molar",
)

# Outlet pressure = inlet pressure × this ratio for the PH-flash snapshot.
PH_FLASH_PRESSURE_RATIO: float = 1.5

# Strict per-property drift tolerances — shared between TP and PH snapshots.
PROPERTY_TOLERANCES: dict[str, dict[str, float]] = {
    "z": {"rel_tol": 1.0e-8, "abs_tol": 0.0},
    "density": {"rel_tol": 2.0e-8, "abs_tol": 0.0},
    "kappa": {"rel_tol": 1.0e-8, "abs_tol": 0.0},
    # Avoid meaningless relative failures near zero.
    "enthalpy_joule_per_kg": {"rel_tol": 1.0e-6, "abs_tol": 1.0e-2},
    "vapor_fraction_molar": {"rel_tol": 0.0, "abs_tol": 2.0e-8},
    # Composition-derived and deterministic.
    "molar_mass": {"rel_tol": 1.0e-12, "abs_tol": 0.0},
    # Temperature tolerance for PH-flash outlet (~0.1 mK at 300 K).
    "temperature_kelvin": {"rel_tol": 1.0e-6, "abs_tol": 0.0},
}

# Backward-compatible alias — TP key used by existing snapshot entries and tests.
SNAPSHOT_PROPERTIES = TP_SNAPSHOT_PROPERTIES


def tp_state_key(composition_name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> str:
    return f"tp|{composition_name}|P={pressure_bara:g}bara|T={temperature_kelvin:g}K|{eos_model.value}"


def ph_state_key(composition_name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> str:
    """Key for a PH-flash snapshot entry; inlet P/T identify the state."""
    return f"ph|{composition_name}|Pin={pressure_bara:g}bara|T={temperature_kelvin:g}K|{eos_model.value}"


# Backward-compatible alias used by existing test and regenerate code.
def state_key(composition_name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> str:
    return tp_state_key(composition_name, pressure_bara, temperature_kelvin, eos_model)


def iter_states():
    """Iterate over the full Cartesian product of the snapshot spec,
    plus any composition-specific extra points. Wet compositions are
    skipped at temperatures below their registered floor."""
    for composition_name in COMPOSITION_NAMES:
        for pressure_bara, temperature_kelvin in PRESSURE_TEMPERATURE_POINTS_BARA_KELVIN:
            if not is_state_supported(composition_name, temperature_kelvin):
                continue
            for eos_model in EOS_MODELS:
                yield composition_name, pressure_bara, temperature_kelvin, eos_model
        for pressure_bara, temperature_kelvin in EXTRA_POINTS_PER_COMPOSITION_BARA_KELVIN.get(composition_name, ()):
            if not is_state_supported(composition_name, temperature_kelvin):
                continue
            for eos_model in EOS_MODELS:
                yield composition_name, pressure_bara, temperature_kelvin, eos_model
