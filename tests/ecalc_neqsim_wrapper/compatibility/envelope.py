"""Single source of truth for the operating envelope ecalc exercises NeqSim over.

Every state-generating helper in the compatibility suite (sanity grids,
trajectory continuity samples, regression spec) reads the envelope from
this module instead of carrying its own ad-hoc constants. When ecalc's
real envelope changes (a new MAX_FIRST_GUESS_BAR cap, a new EoS, a
new operation), update it here in one place.

The envelope captures four orthogonal dimensions:

* **Pressure**: 1 to MAX_FIRST_GUESS_BAR=2000 bara. The upper bound is
  the cap the compressor solver applies to its first-guess outlet
  pressure during max-speed probes
  (compressor/core/train/utils/common.py).
* **Temperature**: 250 to 460 K. The upper bound is the per-stage
  PH-flash outlet under off-design conditions
  (~185 kJ/kg head over Cp ~2200 J/(kg.K) ≈ 84 K rise from a 295 K
  inlet, plus margin for low-Cp gas). The lower bound is colder than
  any compressor inlet ecalc actually uses; states below water's
  freezing point are filtered out for water-bearing compositions via
  ``compositions.is_state_supported``.
* **EoS**: SRK, PR, GERG_SRK, GERG_PR. The four models exposed by the
  YAML schema and reachable through the wrapper.
* **Operations**: TP-flash, PH-flash, remove_liquid, mixing, property
  extraction. The five things ecalc actually calls NeqSim for.
"""

from __future__ import annotations

from libecalc.process.fluid_stream.fluid_model import EoSModel

PRESSURE_MIN_BARA: float = 1.0
PRESSURE_MAX_BARA: float = 2000.0  # MAX_FIRST_GUESS_BAR

TEMPERATURE_MIN_KELVIN: float = 250.0
TEMPERATURE_MAX_KELVIN: float = 460.0

NOMINAL_PRESSURES_BARA: tuple[float, ...] = (1.0, 5.0, 20.0, 50.0, 100.0, 200.0)
NOMINAL_TEMPERATURES_KELVIN: tuple[float, ...] = (250.0, 280.0, 300.0, 330.0, 380.0)

HIGH_PRESSURE_PRESSURES_BARA: tuple[float, ...] = (300.0, 400.0)
HIGH_PRESSURE_TEMPERATURES_KELVIN: tuple[float, ...] = (300.0, 360.0)

MAX_SPEED_PROBE_PRESSURES_BARA: tuple[float, ...] = (500.0, 1000.0, 2000.0)
MAX_SPEED_PROBE_TEMPERATURES_KELVIN: tuple[float, ...] = (400.0, 450.0)


def nominal_grid() -> list[tuple[float, float]]:
    return [(p, t) for p in NOMINAL_PRESSURES_BARA for t in NOMINAL_TEMPERATURES_KELVIN]


def high_pressure_grid() -> list[tuple[float, float]]:
    return [(p, t) for p in HIGH_PRESSURE_PRESSURES_BARA for t in HIGH_PRESSURE_TEMPERATURES_KELVIN]


def max_speed_probe_grid() -> list[tuple[float, float]]:
    return [(p, t) for p in MAX_SPEED_PROBE_PRESSURES_BARA for t in MAX_SPEED_PROBE_TEMPERATURES_KELVIN]


EOS_MODELS: tuple[EoSModel, ...] = (
    EoSModel.SRK,
    EoSModel.PR,
    EoSModel.GERG_SRK,
    EoSModel.GERG_PR,
)
