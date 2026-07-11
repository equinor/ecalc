"""The declarative solver surface: Param/CoupledParameter (vary), Probe, Target, Constraint.

A ``Constraint`` is the adjust-block analogue: vary one parameter until a probed
value meets a target, within bounds; when the parameter saturates at a bound, its
``fallback`` engages (the pressure-control mode). Structural validity is automatic
because ``Param`` is validated at construction; the only extra checks are
FROM_CHART (needs a Shaft owner) and FROM_CAPACITY (needs a recirculation param).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.system import State
from libecalc.process_concept_draft_v3.units import OUT, CommonASVLoop, CompressorStage, Shaft, Unit

if TYPE_CHECKING:
    from libecalc.process_concept_draft_v3.solver.coupled import CoupledParameter

INF = float("inf")
PRESSURE_TOLERANCE = 1e-3  # FloatConstraint default (bara)


@dataclass(frozen=True)
class Bounds:
    lower: float
    upper: float


class FromChart:
    """Speed bounds from the charts of the stages on the owning shaft."""

    def __repr__(self) -> str:
        return "FROM_CHART"


class FromCapacity:
    """Recirculation bounds from the protected first stage's range at solve time."""

    def __repr__(self) -> str:
        return "FROM_CAPACITY"


FROM_CHART = FromChart()
FROM_CAPACITY = FromCapacity()


@dataclass(frozen=True)
class Probe:
    """An observable anchored to a unit (the flow anchor used for sectioning)."""

    read: Callable[[State], float]
    at: Unit

    @staticmethod
    def outlet_pressure(unit: Unit, port: str = OUT) -> Probe:
        return Probe(read=lambda state: state.out(unit, port).pressure_bara, at=unit)

    @staticmethod
    def custom(fn: Callable[[State], float], at: Unit) -> Probe:
        return Probe(read=fn, at=at)


@dataclass(frozen=True)
class Target:
    probe: Probe
    value: float
    tolerance: float = PRESSURE_TOLERANCE


@dataclass
class Constraint:
    """Vary ``vary`` until ``target`` is met within ``bounds``; else engage ``fallback``."""

    vary: Param | CoupledParameter
    target: Target
    bounds: Bounds | FromChart | FromCapacity
    fallback: Constraint | None = None

    def __post_init__(self) -> None:
        if isinstance(self.bounds, FromChart):
            if not (isinstance(self.vary, Param) and isinstance(self.vary.owner, Shaft)):
                raise ValueError("FROM_CHART bounds require the varied parameter to belong to a Shaft.")
        if isinstance(self.bounds, FromCapacity):
            if not (isinstance(self.vary, Param) and _is_recirculation_param(self.vary)):
                raise ValueError("FROM_CAPACITY bounds require a recirculation parameter (stage rate or loop rate).")


def _is_recirculation_param(param: object) -> bool:
    if not isinstance(param, Param):
        return False
    owner = param.owner
    return (isinstance(owner, CompressorStage) and param.field == "recirculation_rate") or (
        isinstance(owner, CommonASVLoop) and param.field == "rate_sm3_per_day"
    )
