"""Spec shared by the snapshot generator and the snapshot test.

Single source of truth for which states are pinned at strict
per-property tolerances. Reads its envelope (P, T, EoS) from
``..envelope`` so a change to the operating envelope propagates
to the snapshot automatically.
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

# Focused snapshot subset spanning light, export, heavy, wet/dry, and CO2-rich gases.
COMPOSITION_NAMES: tuple[str, ...] = (
    "pure_methane",
    "lean_natural_gas",
    "typical_export_gas",
    "c3_rich_wellstream",
    "c3_rich_wellstream_dry",
    "co2_heavy_injection",
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

# Pressure/temperature are inputs; standard_density is not on NeqsimFluid.
SNAPSHOT_PROPERTIES: tuple[str, ...] = (
    "z",
    "density",
    "kappa",
    "enthalpy_joule_per_kg",
    "vapor_fraction_molar",
    "molar_mass",
)

# Strict per-property drift tolerances.
PROPERTY_TOLERANCES: dict[str, dict[str, float]] = {
    "z": {"rel_tol": 1.0e-8, "abs_tol": 0.0},
    "density": {"rel_tol": 2.0e-8, "abs_tol": 0.0},
    "kappa": {"rel_tol": 1.0e-8, "abs_tol": 0.0},
    # Avoid meaningless relative failures near zero.
    "enthalpy_joule_per_kg": {"rel_tol": 1.0e-6, "abs_tol": 1.0e-2},
    "vapor_fraction_molar": {"rel_tol": 0.0, "abs_tol": 2.0e-8},
    # Composition-derived and deterministic.
    "molar_mass": {"rel_tol": 1.0e-12, "abs_tol": 0.0},
}


def state_key(composition_name: str, pressure_bara: float, temperature_kelvin: float, eos_model: EoSModel) -> str:
    """Stable JSON-friendly key for a snapshot state."""
    return f"{composition_name}|P={pressure_bara:g}bara|T={temperature_kelvin:g}K|{eos_model.value}"


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
