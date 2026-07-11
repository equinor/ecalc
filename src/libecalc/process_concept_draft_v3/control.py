"""Local control: the anti-surge controller restores chart feasibility.

``evaluate_with_surge_control`` runs a forward pass with the autonomous ASV controller
live inside it: any recirculation parameter not overridden or suspended is an
*auto* parameter the controller may raise to the minimal restoring value when a
stage falls below its minimum-flow line.

The explicit rules (one branch each, all visible):

- ``RATE_TOO_HIGH`` / other: recirculation cannot help — return as data.
- ``RATE_TOO_LOW`` at a stage wrapped by a common ``CommonASVLoop`` whose
  rate is auto: set the loop to the minimal common-feasible rate (capacity bisect
  at tolerance 1e-2, boundary from the FIRST protected stage).
- ``RATE_TOO_LOW`` at a standalone stage whose own recirculation is auto: add the
  minimal additional rate from the stage's ACTUAL inlet (increments compose).
- ``RATE_TOO_LOW`` with no live auto parameter (suspended/overridden, or idle
  under a common loop) → return as data. **This is the suspension rule.**

Returned auto values live in their own dict — NEVER merged into the caller's
overrides; reported separately from solver-chosen values.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process_concept_draft_v3.params import UNSET, Param
from libecalc.process_concept_draft_v3.solver.numerics import (
    CAPACITY_SEARCH_TOLERANCE,
    DidNotConvergeError,
    binary_search_max,
)
from libecalc.process_concept_draft_v3.system import ProcessSystem, State, ViolationKind
from libecalc.process_concept_draft_v3.units import IN, CommonASVLoop, CompressorStage, Overrides, Unit

MAX_RESTORATION_ITERATIONS = 25


def _speed_of(stage: CompressorStage, values: Mapping[Param, float]) -> float:
    speed = Overrides(values).value(stage.shaft, "speed")
    if speed is UNSET:
        raise ValueError("Shaft speed is UNSET during anti-surge restoration.")
    return float(speed)


def evaluate_with_surge_control(
    system: ProcessSystem,
    overrides: Mapping[Param, float],
    feeds: Mapping[str, FluidStream],
    suspended: frozenset[Param] = frozenset(),
    *,
    section: Sequence[Unit] | None = None,
    inlet: FluidStream | None = None,
) -> tuple[State, dict[Param, float]]:
    fluid_service = system.fluid_service
    units = list(section) if section is not None else system.units
    fixed = set(overrides.keys()) | set(suspended)

    stages = [unit for unit in units if isinstance(unit, CompressorStage)]
    stage_params = {stage: Param(stage, "recirculation_rate") for stage in stages}
    loop_for: dict[CompressorStage, CommonASVLoop | None] = {stage: system.loop_for(stage) for stage in stages}
    loop_params: dict[CommonASVLoop, Param] = {
        loop: Param(loop, "rate_sm3_per_day") for loop in {loop for loop in loop_for.values() if loop is not None}
    }

    autos: dict[Param, float] = {}
    for stage, param in stage_params.items():
        if loop_for[stage] is not None:
            continue  # idle under a common loop — nothing binds to it
        if param not in fixed:
            autos[param] = 0.0
    for param in loop_params.values():
        if param not in fixed:
            autos[param] = 0.0

    state = system.evaluate({**overrides, **autos}, feeds, section=section, inlet=inlet)
    for _ in range(MAX_RESTORATION_ITERATIONS):
        if state.feasible:
            return state, autos
        violation = state.violation
        assert violation is not None
        if violation.kind is not ViolationKind.RATE_TOO_LOW:
            return state, autos

        stage = violation.unit
        if not isinstance(stage, CompressorStage):
            return state, autos

        loop = loop_for.get(stage)
        loop_param = loop_params.get(loop) if loop is not None else None
        if loop is not None and loop_param is not None and loop_param in autos:
            rate = _min_feasible_common_rate(
                system, loop, loop_param, {**overrides, **autos}, feeds, section, inlet, state, fluid_service
            )
            if rate is None:
                return state, autos
            autos[loop_param] = rate
            state = system.evaluate({**overrides, **autos}, feeds, section=section, inlet=inlet)
            continue

        stage_param = stage_params[stage]
        if stage_param in autos:
            speed = _speed_of(stage, {**overrides, **autos})
            recirc_now = autos[stage_param]
            assert violation.inlet_stream is not None
            compressor_inlet = stage.compressor_inlet(violation.inlet_stream, recirc_now, fluid_service)
            additional = stage.recirculation_range(compressor_inlet, speed, fluid_service).min
            if additional <= 0.0:
                return state, autos
            autos[stage_param] += additional
            state = system.evaluate({**overrides, **autos}, feeds, section=section, inlet=inlet)
            continue

        return state, autos  # suspension rule: no live auto parameter at this stage

    return state, autos


def _first_protected_stage(
    system: ProcessSystem, loop: CommonASVLoop, section: Sequence[Unit] | None
) -> CompressorStage | None:
    units = list(section) if section is not None else system.units
    for unit in units:
        if isinstance(unit, CompressorStage) and system.loop_for(unit) is loop:
            return unit
    return None


def _min_feasible_common_rate(
    system: ProcessSystem,
    loop: CommonASVLoop,
    loop_param: Param,
    current_values: Mapping[Param, float],
    feeds: Mapping[str, FluidStream],
    section: Sequence[Unit] | None,
    inlet: FluidStream | None,
    state: State,
    fluid_service: FluidService,
) -> float | None:
    """Smallest common-loop rate keeping every wrapped stage within capacity."""
    first = _first_protected_stage(system, loop, section)
    if first is None:
        return None
    first_inlet = state.streams.get((first, IN))
    if first_inlet is None:
        return None
    speed = _speed_of(first, current_values)
    compressor_inlet = first.compressor_inlet(first_inlet, 0.0, fluid_service)
    boundary = first.recirculation_range(compressor_inlet, speed, fluid_service)

    def attempt(rate: float) -> State:
        return system.evaluate({**current_values, loop_param: rate}, feeds, section=section, inlet=inlet)

    result = attempt(boundary.min)
    if result.feasible:
        return boundary.min
    if result.violation is None or result.violation.kind is not ViolationKind.RATE_TOO_LOW:
        return None

    def probe(rate: float) -> tuple[bool, bool]:
        trial = attempt(rate)
        if trial.feasible:
            return False, True
        if trial.violation is not None and trial.violation.kind is ViolationKind.RATE_TOO_LOW:
            return True, False
        return False, False

    try:
        return binary_search_max(boundary.min, boundary.max, probe, tolerance=CAPACITY_SEARCH_TOLERANCE)
    except DidNotConvergeError:
        return None
