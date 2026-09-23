from __future__ import annotations

from libecalc.common.ddd import value_object
from libecalc.energy.energy_failure import EnergyFailure
from libecalc.energy.energy_types import Energy


@value_object
class EnergyUnitState:
    """What a single energy unit did at one operational point.

    Holds values only, so an energy network can be stored and recreated without the units that
    produced it. The two energy fields mirror the unit's energy types: `input_energy` is None for
    a unit that draws nothing, such as a source, and `output_energy` is None for a unit that
    delivers nothing downstream, such as a consumer.
    """

    output_energy: Energy | None
    input_energy: Energy | None
    capacity: Energy | None
    failures: tuple[EnergyFailure, ...] = ()

    def is_feasible(self) -> bool:
        return not self.failures
