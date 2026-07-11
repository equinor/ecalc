"""Coupled parameters: one scalar driving N stage recirculation rates via a rule.

A ``CoupledParameter`` keeps every solve 1D. Two distribution rules reproduce the
individual-ASV pressure-control strategies:

- BALANCED_RATE: one fraction of each stage's available capacity
  (``rate_i = min_i + fraction * (max_i - min_i)``), the boundary read from each
  stage's ACTUAL inlet in flow order (sequential — stage i depends on the rates
  already assigned upstream). The solver root-finds the fraction in [0, 1].
- BALANCED_PRESSURE: equal pressure ratio per stage. This is NOT a scalar map; it
  expands into a sequence of per-stage 1D solves (each stage's rate vs its own
  equal-ratio stage target), in flow order.

``equal_ratio_targets`` splits a total pressure ratio into per-section targets for
independent-shaft (multi-shaft) constraint lists.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process_concept_draft_v3.control import evaluate_with_surge_control
from libecalc.process_concept_draft_v3.params import UNSET, Param
from libecalc.process_concept_draft_v3.solver.constraints import Constraint
from libecalc.process_concept_draft_v3.solver.numerics import DidNotConvergeError, find_root
from libecalc.process_concept_draft_v3.solver.result import (
    SolverFailure,
    TargetDirection,
    TargetUnreachableFailure,
    failure_from_violation,
)
from libecalc.process_concept_draft_v3.system import IN, ProcessSystem, State
from libecalc.process_concept_draft_v3.units import OUT, CompressorStage, Overrides, Unit


class DistributionRule(Enum):
    BALANCED_RATE = "balanced_rate"
    BALANCED_PRESSURE = "balanced_pressure"


@dataclass(frozen=True)
class CoupledParameter:
    """One scalar driving N unit parameters via a rule. The solver sees ONE 1D variable."""

    name: str
    params: tuple[Param, ...]
    rule: DistributionRule


@dataclass
class CoupledSolution:
    values: dict[Param, float]
    auto_values: dict[Param, float]
    state: State | None
    failure: SolverFailure | None = None


def equal_ratio_targets(total_target: float, inlet_pressure: float, n_sections: int) -> list[float]:
    """Per-section pressure targets with equal ratios; the last is exactly the total target."""
    if n_sections <= 0:
        return []
    ratio = (total_target / inlet_pressure) ** (1.0 / n_sections)
    current = inlet_pressure
    targets: list[float] = []
    for _ in range(n_sections):
        current *= ratio
        targets.append(current)
    targets[-1] = total_target
    return targets


def _ordered_pairs(
    system: ProcessSystem, params: Sequence[Param], section: Sequence[Unit] | None
) -> list[tuple[Param, CompressorStage]]:
    pairs = [(param, param.owner) for param in params if isinstance(param.owner, CompressorStage)]
    order = list(section) if section is not None else system.units
    position = {unit: index for index, unit in enumerate(order)}
    pairs.sort(key=lambda pair: position.get(pair[1], system.units.index(pair[1])))
    return pairs


def _staged_rates(
    system: ProcessSystem,
    pairs: list[tuple[Param, CompressorStage]],
    fraction: float,
    base: Mapping[Param, float],
    feeds: Mapping[str, FluidStream],
    section: Sequence[Unit] | None,
    inlet: FluidStream | None,
) -> dict[Param, float] | None:
    """Per-stage rate = min + fraction * (max - min), each from the stage's actual inlet."""
    values: dict[Param, float] = {**base, **{param: 0.0 for param, _ in pairs}}
    for param, stage in pairs:
        state = system.evaluate(values, feeds, section=section, inlet=inlet)
        stage_inlet = state.streams.get((stage, IN))
        if stage_inlet is None:
            return None
        speed = Overrides(values).value(stage.shaft, "speed")
        if speed is UNSET:
            return None
        compressor_inlet = stage.compressor_inlet(stage_inlet, 0.0, system.fluid_service)
        boundary = stage.recirculation_range(compressor_inlet, float(speed), system.fluid_service)
        values[param] = boundary.min + fraction * (boundary.max - boundary.min)
    return {param: values[param] for param, _ in pairs}


def solve_balanced(
    system: ProcessSystem,
    fallback: Constraint,
    base: dict[Param, float],
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
    baseline_state: State,
) -> CoupledSolution:
    coupled = fallback.vary
    assert isinstance(coupled, CoupledParameter)
    if coupled.rule is DistributionRule.BALANCED_RATE:
        return _solve_balanced_rate(system, fallback, coupled, base, feeds, inlet, section)
    return _solve_balanced_pressure(system, fallback, coupled, base, feeds, inlet, section, baseline_state)


def _solve_balanced_rate(
    system: ProcessSystem,
    fallback: Constraint,
    coupled: CoupledParameter,
    base: dict[Param, float],
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
) -> CoupledSolution:
    target = fallback.target
    pairs = _ordered_pairs(system, coupled.params, section)
    suspended = frozenset(coupled.params)

    def outlet_at(fraction: float) -> tuple[State | None, dict[Param, float] | None, dict[Param, float]]:
        values = _staged_rates(system, pairs, fraction, base, feeds, section, inlet)
        if values is None:
            return None, None, {}
        state, autos = evaluate_with_surge_control(
            system, {**base, **values}, feeds, suspended=suspended, section=section, inlet=inlet
        )
        return state, values, autos

    floor_state, floor_values, floor_autos = outlet_at(1.0)
    if floor_state is None or not floor_state.feasible:
        failure = failure_from_violation(floor_state.violation) if floor_state and floor_state.violation else None
        return CoupledSolution(dict(base), {}, floor_state, failure)
    pressure_floor = target.probe.read(floor_state)
    if pressure_floor > target.value + target.tolerance:
        return CoupledSolution(
            {**base, **(floor_values or {})},
            floor_autos,
            floor_state,
            TargetUnreachableFailure(target.probe, pressure_floor, target.value, TargetDirection.MIN_ABOVE_TARGET),
        )

    def residual(fraction: float) -> float:
        state, _, _ = outlet_at(fraction)
        if state is None or not state.feasible:
            raise DidNotConvergeError(0.0, 1.0, 0.0, 0)
        return target.probe.read(state) - target.value

    root = find_root(0.0, 1.0, residual)
    state, values, autos = outlet_at(root)
    assert state is not None and values is not None
    if not state.feasible:
        assert state.violation is not None
        return CoupledSolution({**base, **values}, autos, state, failure_from_violation(state.violation))
    return CoupledSolution({**base, **values}, autos, state)


def _solve_balanced_pressure(
    system: ProcessSystem,
    fallback: Constraint,
    coupled: CoupledParameter,
    base: dict[Param, float],
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
    baseline_state: State,
) -> CoupledSolution:
    target = fallback.target
    pairs = _ordered_pairs(system, coupled.params, section)
    suspended = frozenset(coupled.params)

    # Minimum achievable pressure: every stage at maximum recirculation.
    floor_values = _staged_rates(system, pairs, 1.0, base, feeds, section, inlet)
    if floor_values is not None:
        floor_state, _ = evaluate_with_surge_control(
            system, {**base, **floor_values}, feeds, suspended=suspended, section=section, inlet=inlet
        )
        if floor_state.feasible:
            pressure_floor = target.probe.read(floor_state)
            if pressure_floor > target.value + target.tolerance:
                return CoupledSolution(
                    {**base, **floor_values},
                    {},
                    floor_state,
                    TargetUnreachableFailure(
                        target.probe, pressure_floor, target.value, TargetDirection.MIN_ABOVE_TARGET
                    ),
                )

    units = list(section) if section is not None else system.units
    section_inlet = baseline_state.streams.get((units[0], IN))
    if section_inlet is None:
        return CoupledSolution(dict(base), {}, baseline_state, None)
    inlet_pressure = section_inlet.pressure_bara
    ratio_per_stage = (target.value / inlet_pressure) ** (1.0 / len(pairs))

    values: dict[Param, float] = {**base, **{param: 0.0 for param, _ in pairs}}
    for index, (param, stage) in enumerate(pairs):
        stage_target = inlet_pressure * ratio_per_stage ** (index + 1)
        state = system.evaluate(values, feeds, section=section, inlet=inlet)
        stage_inlet = state.streams.get((stage, IN))
        if stage_inlet is None:
            failure = failure_from_violation(state.violation) if state.violation else None
            return CoupledSolution(values, {}, state, failure)
        speed = Overrides(values).value(stage.shaft, "speed")
        compressor_inlet = stage.compressor_inlet(stage_inlet, 0.0, system.fluid_service)
        boundary = stage.recirculation_range(compressor_inlet, float(speed), system.fluid_service)

        def stage_residual(
            x: float, _param: Param = param, _stage: CompressorStage = stage, _target: float = stage_target
        ) -> float:
            trial_state = system.evaluate({**values, _param: x}, feeds, section=section, inlet=inlet)
            if (_stage, OUT) not in trial_state.streams:
                raise DidNotConvergeError(boundary.min, boundary.max, 0.0, 0)
            return trial_state.out(_stage).pressure_bara - _target

        residual_low = stage_residual(boundary.min)
        residual_high = stage_residual(boundary.max)
        if abs(residual_low) <= target.tolerance:
            values[param] = boundary.min
        elif abs(residual_high) <= target.tolerance:
            values[param] = boundary.max
        elif residual_low > 0 > residual_high:
            values[param] = find_root(boundary.min, boundary.max, stage_residual)
        else:
            direction = TargetDirection.MIN_ABOVE_TARGET if residual_high > 0 else TargetDirection.MAX_BELOW_TARGET
            achievable = stage_target + (residual_high if residual_high > 0 else residual_low)
            return CoupledSolution(
                values,
                {},
                state,
                TargetUnreachableFailure(target.probe, achievable, stage_target, direction),
            )

    final_state, autos = evaluate_with_surge_control(
        system, values, feeds, suspended=suspended, section=section, inlet=inlet
    )
    if not final_state.feasible:
        assert final_state.violation is not None
        return CoupledSolution(values, autos, final_state, failure_from_violation(final_state.violation))
    return CoupledSolution(values, autos, final_state)
