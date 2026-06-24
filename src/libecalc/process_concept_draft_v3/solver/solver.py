"""The constraint solver: a primary 1D search with typed endpoint verdicts and a
fallback chain that reproduces the pressure-control modes.

Single-target solving and multi-section orchestration with the binding-section
rule. Anti-surge restoration is externalized into ``evaluate_with_surge_control`` — every
residual probe is a CONTROLLED evaluation, so the ASV reflex is live inside each
one.

Discipline (parity-load-bearing):

- Primary endpoint verdicts use STRICT ``<`` / ``>``.
- Pinned-state and fallback checks use ``target.tolerance``.
- Root finding rtol 1e-5; capacity bisects tolerance 1e-2.
- The downstream choke is analytic (one subtraction); the train compresses to the
  fictitious higher pressure its curve delivers and the valve subtracts the rest.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process_concept_draft_v3.control import evaluate_with_surge_control
from libecalc.process_concept_draft_v3.params import UNSET, Param
from libecalc.process_concept_draft_v3.solver.constraints import (
    Bounds,
    Constraint,
    FromCapacity,
    FromChart,
    _is_recirculation_param,
)
from libecalc.process_concept_draft_v3.solver.coupled import CoupledParameter, solve_balanced
from libecalc.process_concept_draft_v3.solver.numerics import (
    CAPACITY_SEARCH_TOLERANCE,
    DidNotConvergeError,
    binary_search_max,
    find_root,
)
from libecalc.process_concept_draft_v3.solver.result import (
    SolverFailure,
    SolverResult,
    TargetDirection,
    TargetUnreachableFailure,
    failure_from_violation,
)
from libecalc.process_concept_draft_v3.system import IN, ProcessSystem, State, ViolationKind
from libecalc.process_concept_draft_v3.units import (
    OUT,
    Choke,
    CommonASVLoop,
    CompressorStage,
    Overrides,
    Shaft,
    Unit,
)

_BISECT_TOLERANCE = 1e-3
_CHOKE_CAP_TOLERANCE = 1e-3
_ZERO_RATE_SM3_PER_DAY = 1e-3  # below this the feed is idle by convention (no compression)


@dataclass
class _SectionSolution:
    values: dict[Param, float]
    auto_values: dict[Param, float]
    state: State | None
    failure: SolverFailure | None = None


@dataclass
class _PrimaryOutcome:
    solved: float | None = None
    pinned: float | None = None
    values: dict[Param, float] = field(default_factory=dict)
    auto_values: dict[Param, float] = field(default_factory=dict)
    state: State | None = None
    failure: SolverFailure | None = None


# --------------------------------------------------------------------- bounds


def _stages_on_shaft(system: ProcessSystem, shaft: Shaft) -> list[CompressorStage]:
    return [u for u in system.units if isinstance(u, CompressorStage) and u.shaft is shaft]


def speed_bounds(system: ProcessSystem, shaft: Shaft) -> Bounds:
    """FROM_CHART speed bounds: max of chart minimum speeds, min of maximum speeds."""
    stages = _stages_on_shaft(system, shaft)
    if not stages:
        raise ValueError("FROM_CHART bounds: the shaft has no compressor stages in this system.")
    charts = [CompressorChart(stage.chart) for stage in stages]
    lower = max(chart.minimum_speed for chart in charts)
    upper = min(chart.maximum_speed for chart in charts)
    if lower > upper:
        raise ValueError(
            "FROM_CHART bounds resolve to an empty speed interval: the stages on this shaft have "
            "incompatible (disjoint) speed ranges."
        )
    return Bounds(lower=lower, upper=upper)


def _resolve_primary_bounds(system: ProcessSystem, constraint: Constraint) -> Bounds:
    if isinstance(constraint.bounds, Bounds):
        return constraint.bounds
    if isinstance(constraint.bounds, FromChart):
        assert isinstance(constraint.vary, Param)
        owner = constraint.vary.owner
        assert isinstance(owner, Shaft)
        return speed_bounds(system, owner)
    raise ValueError("FROM_CAPACITY is only valid on a recirculation fallback, not on the primary.")


def _first_protected_stage(system: ProcessSystem, loop: CommonASVLoop, section: Sequence[Unit] | None):
    units = list(section) if section is not None else system.units
    for unit in units:
        if isinstance(unit, CompressorStage) and system.loop_for(unit) is loop:
            return unit
    return None


def _resolve_fallback_bounds(
    system: ProcessSystem,
    fallback: Constraint,
    base: Mapping[Param, float],
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
    baseline_state: State,
) -> Bounds | None:
    vary = fallback.vary
    assert isinstance(vary, Param)

    if isinstance(fallback.bounds, Bounds):
        bounds = fallback.bounds
        if isinstance(vary.owner, Choke):
            choke = vary.owner
            try:
                inlet_pressure = baseline_state.inlet(choke).pressure_bara
            except KeyError:
                return bounds
            return Bounds(bounds.lower, min(bounds.upper, inlet_pressure - _CHOKE_CAP_TOLERANCE))
        return bounds

    if isinstance(fallback.bounds, FromCapacity):
        owner = vary.owner
        if isinstance(owner, CommonASVLoop):
            stage = _first_protected_stage(system, owner, section)
            if stage is None:
                return None
            # The common loop is an upstream unit, so the protected stage's inlet already
            # reflects whatever loop rate is set. Evaluate with the loop OFF to read the
            # inlet free of recirculation, giving the ABSOLUTE loop-rate range.
            zero_state = system.evaluate({**base, vary: 0.0}, feeds, section=section, inlet=inlet)
            stage_inlet = zero_state.streams.get((stage, IN))
            own_recirc = 0.0
        elif isinstance(owner, CompressorStage):
            stage = owner
            stage_inlet = baseline_state.streams.get((stage, IN))
            own_recirc = 0.0
        else:
            return None
        if stage_inlet is None:
            return None
        speed = Overrides(base).value(stage.shaft, "speed")
        if speed is UNSET:
            return None
        compressor_inlet = stage.compressor_inlet(stage_inlet, own_recirc, system.fluid_service)
        boundary = stage.recirculation_range(compressor_inlet, float(speed), system.fluid_service)
        return Bounds(lower=boundary.min, upper=boundary.max)

    raise ValueError("Unsupported fallback bounds.")


# --------------------------------------------------------------------- section solve


def _solve_section(
    system: ProcessSystem,
    constraint: Constraint,
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
    pinned_primary: float | None,
) -> _SectionSolution:
    vary = constraint.vary
    assert isinstance(vary, Param)
    target = constraint.target

    if pinned_primary is None:
        outcome = _solve_primary(system, constraint, feeds, inlet, section)
        if outcome.failure is not None:
            return _SectionSolution(outcome.values, outcome.auto_values, outcome.state, outcome.failure)
        if outcome.solved is not None:
            return _SectionSolution(outcome.values, outcome.auto_values, outcome.state)
        assert outcome.pinned is not None
        pinned = outcome.pinned
    else:
        pinned = pinned_primary

    base = {vary: pinned}
    state, autos = evaluate_with_surge_control(system, base, feeds, section=section, inlet=inlet)
    values = dict(base)
    if not state.feasible:
        assert state.violation is not None
        return _SectionSolution(values, autos, state, failure_from_violation(state.violation))

    pressure = target.probe.read(state)
    if pressure < target.value - target.tolerance:
        return _SectionSolution(
            values,
            autos,
            state,
            TargetUnreachableFailure(target.probe, pressure, target.value, TargetDirection.MAX_BELOW_TARGET),
        )
    if abs(pressure - target.value) <= target.tolerance:
        return _SectionSolution(values, autos, state)
    if constraint.fallback is None:
        return _SectionSolution(
            values,
            autos,
            state,
            TargetUnreachableFailure(target.probe, pressure, target.value, TargetDirection.MIN_ABOVE_TARGET),
        )
    return _solve_fallback(system, constraint.fallback, base, feeds, inlet, section, state)


def _solve_primary(
    system: ProcessSystem,
    constraint: Constraint,
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
) -> _PrimaryOutcome:
    vary = constraint.vary
    assert isinstance(vary, Param)
    target = constraint.target
    bounds = _resolve_primary_bounds(system, constraint)
    suspended = frozenset({vary}) if _is_recirculation_param(vary) else frozenset()

    def run_at(value: float) -> tuple[State, dict[Param, float]]:
        return evaluate_with_surge_control(
            system, {vary: value}, feeds, suspended=suspended, section=section, inlet=inlet
        )

    state_max, autos_max = run_at(bounds.upper)
    if not state_max.feasible:
        assert state_max.violation is not None
        return _PrimaryOutcome(
            values={vary: bounds.upper},
            auto_values=autos_max,
            state=state_max,
            failure=failure_from_violation(state_max.violation),
        )
    pressure_max = target.probe.read(state_max)
    if pressure_max < target.value:  # STRICT comparison
        return _PrimaryOutcome(
            values={vary: bounds.upper},
            auto_values=autos_max,
            state=state_max,
            failure=TargetUnreachableFailure(
                target.probe, pressure_max, target.value, TargetDirection.MAX_BELOW_TARGET
            ),
        )

    low = bounds.lower
    state_min, autos_min = run_at(low)
    if not state_min.feasible:
        assert state_min.violation is not None
        if state_min.violation.kind is not ViolationKind.RATE_TOO_HIGH:
            return _PrimaryOutcome(
                values={vary: low},
                auto_values=autos_min,
                state=state_min,
                failure=failure_from_violation(state_min.violation),
            )

        def bool_probe(value: float) -> tuple[bool, bool]:
            state, _ = run_at(value)
            if state.feasible:
                return False, True
            if state.violation is not None and state.violation.kind is ViolationKind.RATE_TOO_HIGH:
                return True, False
            return False, False

        try:
            low = binary_search_max(bounds.lower, bounds.upper, bool_probe, max_iter=100)
        except DidNotConvergeError:
            return _PrimaryOutcome(
                values={vary: bounds.lower},
                auto_values=autos_min,
                state=state_min,
                failure=failure_from_violation(state_min.violation),
            )
        state_min, autos_min = run_at(low)
        if (
            not state_min.feasible
            and state_min.violation is not None
            and (state_min.violation.kind is ViolationKind.RATE_TOO_HIGH)
        ):
            # The bisection landed a hair below the feasibility boundary (R1/R6): nudge the
            # speed up by small relative steps until it clears the stonewall (D7 attempt).
            span = bounds.upper - bounds.lower
            for step in range(1, 6):
                nudged = min(low + span * 1e-4 * step, bounds.upper)
                state_min, autos_min = run_at(nudged)
                if state_min.feasible:
                    low = nudged
                    break
        if not state_min.feasible:
            assert state_min.violation is not None
            return _PrimaryOutcome(
                values={vary: low},
                auto_values=autos_min,
                state=state_min,
                failure=failure_from_violation(state_min.violation),
            )

    pressure_min = target.probe.read(state_min)
    if pressure_min > target.value:  # STRICT: saturated low; caller escalates or fails MIN_ABOVE
        return _PrimaryOutcome(pinned=low, values={vary: low}, auto_values=autos_min, state=state_min)

    def residual(value: float) -> float:
        state, _ = run_at(value)
        if not state.feasible:
            raise DidNotConvergeError(low, bounds.upper, 0.0, 0)
        return target.probe.read(state) - target.value

    root = find_root(low, bounds.upper, residual)
    state, autos = run_at(root)
    return _PrimaryOutcome(solved=root, values={vary: root}, auto_values=autos, state=state)


# --------------------------------------------------------------------- fallback solve


def _solve_fallback(
    system: ProcessSystem,
    fallback: Constraint,
    base: dict[Param, float],
    feeds: Mapping[str, FluidStream],
    inlet: FluidStream | None,
    section: Sequence[Unit] | None,
    baseline_state: State,
) -> _SectionSolution:
    vary = fallback.vary

    # CoupledParameter fallback (balanced individual-ASV modes).
    if isinstance(vary, CoupledParameter):
        coupled_solution = solve_balanced(system, fallback, base, feeds, inlet, section, baseline_state)
        return _SectionSolution(
            coupled_solution.values,
            coupled_solution.auto_values,
            coupled_solution.state,
            coupled_solution.failure,
        )

    assert isinstance(vary, Param)
    target = fallback.target
    suspended = frozenset({vary})

    def evaluate(value: float) -> tuple[State, dict[Param, float]]:
        return evaluate_with_surge_control(
            system, {**base, vary: value}, feeds, suspended=suspended, section=section, inlet=inlet
        )

    # Analytic downstream choke: affine residual with slope -1.
    if isinstance(vary.owner, Choke) and target.probe.at is vary.owner:
        baseline_pressure = target.probe.read(baseline_state)
        delta_pressure = baseline_pressure - target.value
        return _finalize_fallback(evaluate, {**base, vary: delta_pressure}, vary, delta_pressure)

    bounds = _resolve_fallback_bounds(system, fallback, base, feeds, inlet, section, baseline_state)
    if bounds is None:
        failure = failure_from_violation(baseline_state.violation) if baseline_state.violation is not None else None
        return _SectionSolution(dict(base), {}, baseline_state, failure)

    # Does pushing the actuator to its upper bound hit the stonewall? (e.g. an upstream
    # choke increasing the rate.) A rate-too-high failure is reported
    # rather than "target unreachable" when the achievable floor still overshoots the target.
    upper_state, _ = evaluate(bounds.upper)
    stonewall_violation = (
        upper_state.violation
        if not upper_state.feasible
        and upper_state.violation is not None
        and upper_state.violation.kind is ViolationKind.RATE_TOO_HIGH
        else None
    )

    low = _trim_feasible_low(evaluate, bounds)
    high = _trim_feasible_high(evaluate, bounds, low)
    if low is None or high is None or high < low:
        state, autos = evaluate(bounds.lower if low is None else low)
        if state.violation is not None:
            failure = failure_from_violation(state.violation)
        else:
            failure = TargetUnreachableFailure(
                target.probe,
                target.probe.read(state) if state.feasible else float("nan"),
                target.value,
                TargetDirection.MIN_ABOVE_TARGET,
            )
        return _SectionSolution(dict(base), autos, state, failure)

    state_high, _ = evaluate(high)
    pressure_floor = target.probe.read(state_high)
    if pressure_floor > target.value + target.tolerance:
        if fallback.fallback is not None:
            return _solve_fallback(system, fallback.fallback, {**base, vary: high}, feeds, inlet, section, state_high)
        if stonewall_violation is not None:
            # The actuator cannot push further without exceeding the maximum flow.
            return _SectionSolution({**base, vary: high}, {}, state_high, failure_from_violation(stonewall_violation))
        return _SectionSolution(
            {**base, vary: high},
            {},
            state_high,
            TargetUnreachableFailure(target.probe, pressure_floor, target.value, TargetDirection.MIN_ABOVE_TARGET),
        )
    if abs(pressure_floor - target.value) <= target.tolerance:
        return _finalize_fallback(evaluate, {**base, vary: high}, vary, high)

    state_low, _ = evaluate(low)
    pressure_ceiling = target.probe.read(state_low)
    if pressure_ceiling < target.value - target.tolerance:
        return _SectionSolution(
            {**base, vary: low},
            {},
            state_low,
            TargetUnreachableFailure(target.probe, pressure_ceiling, target.value, TargetDirection.MAX_BELOW_TARGET),
        )
    if abs(pressure_ceiling - target.value) <= target.tolerance:
        return _finalize_fallback(evaluate, {**base, vary: low}, vary, low)

    def residual(value: float) -> float:
        state, _ = evaluate(value)
        if not state.feasible:
            raise DidNotConvergeError(low, high, 0.0, 0)
        return target.probe.read(state) - target.value

    root = find_root(low, high, residual)
    return _finalize_fallback(evaluate, {**base, vary: root}, vary, root)


def _finalize_fallback(evaluate, values: dict[Param, float], vary: Param, value: float) -> _SectionSolution:
    state, autos = evaluate(value)
    if not state.feasible:
        assert state.violation is not None
        return _SectionSolution(values, autos, state, failure_from_violation(state.violation))
    return _SectionSolution(values, autos, state)


def _trim_feasible_low(evaluate, bounds: Bounds) -> float | None:
    state, _ = evaluate(bounds.lower)
    if state.feasible:
        return bounds.lower
    if state.violation is not None and state.violation.kind is ViolationKind.RATE_TOO_HIGH:
        return None

    def bool_probe(value: float) -> tuple[bool, bool]:
        s, _ = evaluate(value)
        if s.feasible:
            return False, True
        if s.violation is not None and s.violation.kind is ViolationKind.RATE_TOO_LOW:
            return True, False
        return False, False

    try:
        return binary_search_max(bounds.lower, bounds.upper, bool_probe, tolerance=CAPACITY_SEARCH_TOLERANCE)
    except DidNotConvergeError:
        return None


def _trim_feasible_high(evaluate, bounds: Bounds, known_feasible_low: float | None) -> float | None:
    state, _ = evaluate(bounds.upper)
    if state.feasible:
        return bounds.upper
    if known_feasible_low is None:
        return None
    low, high = known_feasible_low, bounds.upper
    while high - low > _BISECT_TOLERANCE:
        mid = (low + high) / 2
        state, _ = evaluate(mid)
        if state.feasible:
            low = mid
        else:
            high = mid
    return low


# --------------------------------------------------------------------- public


def _assemble(system: ProcessSystem, solutions: list[_SectionSolution]) -> SolverResult:
    values: dict[Param, float] = {}
    auto_values: dict[Param, float] = {}
    for solution in solutions:
        values.update(solution.values)
        auto_values.update(solution.auto_values)
    failure = next((s.failure for s in solutions if s.failure is not None), None)
    state = solutions[-1].state if solutions else None
    return SolverResult(
        success=failure is None,
        values=values,
        auto_values=auto_values,
        state=state,
        failure=failure,
    )


def _section_outlet(state: State | None, units: Sequence[Unit]) -> FluidStream | None:
    if state is None:
        return None
    return state.streams.get((units[-1], OUT))


def _build_sections(system: ProcessSystem, constraints: Sequence[Constraint]) -> list[tuple[Constraint, list[Unit]]]:
    """Cut the unit sequence at each target's flow anchor; positions strictly increasing."""
    positioned: list[tuple[int, Constraint]] = []
    for constraint in constraints:
        anchor = constraint.target.probe.at
        if anchor not in system.units:
            raise ValueError("A target probe is anchored to a unit that is not in the system.")
        positioned.append((system.units.index(anchor), constraint))
    positioned.sort(key=lambda pair: pair[0])
    for previous, current in zip(positioned, positioned[1:], strict=False):
        if current[0] <= previous[0]:
            raise ValueError("Target probe anchors must be strictly increasing in flow order.")

    sections: list[tuple[Constraint, list[Unit]]] = []
    start = 0
    for index, (position, constraint) in enumerate(positioned):
        end = len(system.units) if index == len(positioned) - 1 else position + 1
        units = system.units[start:end]
        if not units:
            raise ValueError("A target yields an empty section.")
        start = end
        sections.append((constraint, units))
    return sections


def _shared_primary(constraints: Sequence[Constraint]) -> Param | None:
    if len(constraints) < 2:
        return None
    primaries = [c.vary for c in constraints]
    if not all(isinstance(p, Param) for p in primaries):
        return None
    first = primaries[0]
    if all(p == first for p in primaries):
        return first  # type: ignore[return-value]
    return None


def _validate_placement(sections: list[tuple[Constraint, list[Unit]]]) -> None:
    """Upstream-choke fallback only on the first section; downstream-choke only on the last."""
    last = len(sections) - 1
    for index, (constraint, _units) in enumerate(sections):
        fallback = constraint.fallback
        if fallback is None or not isinstance(fallback.vary, Param) or not isinstance(fallback.vary.owner, Choke):
            continue
        is_downstream = fallback.target.probe.at is fallback.vary.owner
        if is_downstream and index != last:
            raise ValueError("A downstream-choke fallback is only valid on the last section.")
        if not is_downstream and index != 0:
            raise ValueError("An upstream-choke fallback is only valid on the first section.")


def _finish(
    system: ProcessSystem,
    solutions: list[_SectionSolution],
    feeds: Mapping[str, FluidStream],
    n_sections: int,
    failure: SolverFailure | None,
) -> SolverResult:
    values: dict[Param, float] = {}
    auto_values: dict[Param, float] = {}
    for solution in solutions:
        values.update(solution.values)
        auto_values.update(solution.auto_values)
    if failure is None:
        failure = next((s.failure for s in solutions if s.failure is not None), None)
    if solutions and len(solutions) == n_sections:
        # All params (primary + engaged fallbacks + autos) fully specify the system: one
        # uncontrolled pass reproduces the contiguous section sweep and gives a full state.
        state: State | None = system.evaluate({**values, **auto_values}, feeds)
    else:
        state = solutions[-1].state if solutions else None
    return SolverResult(
        success=failure is None and (state is None or state.feasible),
        values=values,
        auto_values=auto_values,
        state=state,
        failure=failure,
    )


def _solve_independent(
    system: ProcessSystem,
    sections: list[tuple[Constraint, list[Unit]]],
    feeds: Mapping[str, FluidStream],
) -> SolverResult:
    solutions: list[_SectionSolution] = []
    failure: SolverFailure | None = None
    inlet: FluidStream | None = None
    for constraint, units in sections:
        solution = _solve_section(system, constraint, feeds, inlet, units, None)
        solutions.append(solution)
        if solution.failure is not None and failure is None:
            failure = solution.failure
        outlet = _section_outlet(solution.state, units)
        if outlet is None:
            return _finish(system, solutions, feeds, len(sections), failure or solution.failure)
        inlet = outlet
    return _finish(system, solutions, feeds, len(sections), failure)


def _solve_binding(
    system: ProcessSystem,
    sections: list[tuple[Constraint, list[Unit]]],
    feeds: Mapping[str, FluidStream],
    shared: Param,
) -> SolverResult:
    _validate_placement(sections)

    # Phase 1: each section solved independently, outlets feeding the next inlet.
    phase1: list[_SectionSolution] = []
    inlet: FluidStream | None = None
    for constraint, units in sections:
        solution = _solve_section(system, constraint, feeds, inlet, units, None)
        if solution.failure is not None:
            return _finish(system, [*phase1, solution], feeds, len(sections), solution.failure)
        phase1.append(solution)
        inlet = _section_outlet(solution.state, units)

    # Phase 2: binding value = the highest primary requirement across sections.
    binding = max(solution.values[shared] for solution in phase1)

    # Phase 3: re-run each section with the primary pinned at the binding value.
    phase3: list[_SectionSolution] = []
    failure: SolverFailure | None = None
    inlet = None
    for constraint, units in sections:
        solution = _solve_section(system, constraint, feeds, inlet, units, binding)
        if solution.failure is not None and failure is None:
            failure = solution.failure
        phase3.append(solution)
        outlet = _section_outlet(solution.state, units)
        if outlet is None:
            return _finish(system, phase3, feeds, len(sections), failure or solution.failure)
        inlet = outlet
    return _finish(system, phase3, feeds, len(sections), failure)


def solve(
    system: ProcessSystem,
    constraints: Sequence[Constraint],
    feeds: Mapping[str, FluidStream],
) -> SolverResult:
    """Solve a process system for one or more constraints.

    One constraint: a single-target solve. Several constraints: cut into sections at
    the target anchors and solve in flow order — independent primaries (multi-shaft)
    or a shared primary via the binding-section rule.
    """
    if not constraints:
        raise ValueError("solve() needs at least one constraint.")

    # Zero-rate convention (domain): a (near-)idle feed needs no compression. Detected
    # before any thermodynamic call and reported as a trivially-successful idle solve.
    if feeds and all(stream.standard_rate_sm3_per_day < _ZERO_RATE_SM3_PER_DAY for stream in feeds.values()):
        return SolverResult(success=True, values={}, auto_values={}, state=None, failure=None)

    if len(constraints) == 1:
        solution = _solve_section(system, constraints[0], feeds, inlet=None, section=None, pinned_primary=None)
        return _assemble(system, [solution])

    sections = _build_sections(system, list(constraints))
    shared = _shared_primary(list(constraints))
    if shared is not None:
        return _solve_binding(system, sections, feeds, shared)
    return _solve_independent(system, sections, feeds)
