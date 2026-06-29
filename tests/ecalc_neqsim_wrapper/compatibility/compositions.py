"""Composition library for the NeqSim compatibility suite.

Each composition is named for its representative class. Compositions are
declared in mole percent and normalised. The set is intended to span the
range of natural-gas / wellstream fluids ecalc realistically encounters,
including known bug-prone cases.
"""

from libecalc.process.fluid_stream.fluid_model import FluidComposition

# Near-pure methane baseline.
PURE_METHANE = FluidComposition(methane=99.99, nitrogen=0.01).normalized()

# Lean sales-gas-like composition.
LEAN_NATURAL_GAS = FluidComposition(
    nitrogen=0.5,
    CO2=1.0,
    methane=95.0,
    ethane=2.5,
    propane=0.7,
    i_butane=0.1,
    n_butane=0.15,
    i_pentane=0.025,
    n_pentane=0.025,
).normalized()

# Typical export gas (~19.4 g/mol).
TYPICAL_EXPORT_GAS = FluidComposition(
    nitrogen=0.74373,
    CO2=2.415619,
    methane=85.60145,
    ethane=6.707826,
    propane=2.611471,
    i_butane=0.45077,
    n_butane=0.691702,
    i_pentane=0.210714,
    n_pentane=0.197937,
    n_hexane=0.368786,
).normalized()

# Rich associated gas close to the dew line.
RICH_ASSOCIATED_GAS = FluidComposition(
    nitrogen=0.682785869,
    CO2=2.466921329,
    methane=79.57192993,
    ethane=5.153816223,
    propane=9.679747581,
    i_butane=0.691399336,
    n_butane=1.174334645,
    i_pentane=0.208390206,
    n_pentane=0.201853022,
    n_hexane=0.16881974,
).normalized()

# C3-rich wellstream, reliably two-phase at moderate pressure.
C3_RICH_WELLSTREAM = FluidComposition(
    water=0.003,
    nitrogen=2.447,
    CO2=0.64,
    methane=41.91,
    ethane=19.9,
    propane=24.29,
    i_butane=3.64,
    n_butane=5.40,
    i_pentane=0.83,
    n_pentane=0.68,
    n_hexane=0.26,
).normalized()

# Dry variant for cold/high-P probes.
C3_RICH_WELLSTREAM_DRY = FluidComposition(
    nitrogen=2.447,
    CO2=0.64,
    methane=41.91,
    ethane=19.9,
    propane=24.29,
    i_butane=3.64,
    n_butane=5.40,
    i_pentane=0.83,
    n_pentane=0.68,
    n_hexane=0.26,
).normalized()

# CO2-heavy injection gas.
CO2_HEAVY_INJECTION = FluidComposition(
    nitrogen=0.5,
    CO2=25.0,
    methane=70.0,
    ethane=3.0,
    propane=1.0,
    i_butane=0.2,
    n_butane=0.3,
).normalized()

# N2-rich gas.
N2_HEAVY = FluidComposition(
    nitrogen=15.0,
    CO2=1.0,
    methane=80.0,
    ethane=3.0,
    propane=1.0,
).normalized()

# Water-bearing lean gas.
WET_LEAN_GAS = FluidComposition(
    water=0.5,
    nitrogen=0.5,
    CO2=1.0,
    methane=92.0,
    ethane=4.0,
    propane=1.5,
    i_butane=0.25,
    n_butane=0.25,
).normalized()


COMPOSITIONS: dict[str, FluidComposition] = {
    "pure_methane": PURE_METHANE,
    "lean_natural_gas": LEAN_NATURAL_GAS,
    "typical_export_gas": TYPICAL_EXPORT_GAS,
    "rich_associated_gas": RICH_ASSOCIATED_GAS,
    "c3_rich_wellstream": C3_RICH_WELLSTREAM,
    "c3_rich_wellstream_dry": C3_RICH_WELLSTREAM_DRY,
    "co2_heavy_injection": CO2_HEAVY_INJECTION,
    "n2_heavy": N2_HEAVY,
    "wet_lean_gas": WET_LEAN_GAS,
}


# NeqSim has no solid-water phase; keep wet compositions above 280 K.
# All state generators consult this registry.
WET_COMPOSITION_TEMPERATURE_FLOOR_KELVIN = 280.0

MIN_TEMPERATURE_KELVIN_PER_COMPOSITION: dict[str, float] = {
    name: WET_COMPOSITION_TEMPERATURE_FLOOR_KELVIN
    for name, composition in COMPOSITIONS.items()
    if getattr(composition, "water", 0.0) > 0.0
}


def min_temperature_kelvin_for(composition_name: str) -> float:
    """Return the minimum temperature at which `composition_name` may
    legitimately be flashed in the compatibility suite. Compositions with
    no entry in the registry have no floor (return -inf)."""
    return MIN_TEMPERATURE_KELVIN_PER_COMPOSITION.get(composition_name, float("-inf"))


def is_state_supported(composition_name: str, temperature_kelvin: float) -> bool:
    """True iff `temperature_kelvin` is at or above the registered floor
    for `composition_name`. Used to filter Cartesian-product state lists."""
    return temperature_kelvin >= min_temperature_kelvin_for(composition_name)
