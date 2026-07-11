"""Solver package: typed failures, certified 1D numerics, constraints, and solve()."""

from libecalc.process_concept_draft_v3.solver.capacity import CapacityResult, Limiter, max_standard_rate
from libecalc.process_concept_draft_v3.solver.constraints import (
    FROM_CAPACITY,
    FROM_CHART,
    INF,
    Bounds,
    Constraint,
    Probe,
    Target,
)
from libecalc.process_concept_draft_v3.solver.coupled import (
    CoupledParameter,
    DistributionRule,
    equal_ratio_targets,
)
from libecalc.process_concept_draft_v3.solver.result import (
    OperationInfeasibleFailure,
    RateTooHighFailure,
    RateTooLowFailure,
    SolverFailure,
    SolverResult,
    TargetDirection,
    TargetUnreachableFailure,
    failure_from_violation,
)
from libecalc.process_concept_draft_v3.solver.solver import solve, speed_bounds

__all__ = [
    "FROM_CAPACITY",
    "FROM_CHART",
    "INF",
    "Bounds",
    "CapacityResult",
    "Constraint",
    "CoupledParameter",
    "DistributionRule",
    "OperationInfeasibleFailure",
    "Limiter",
    "Probe",
    "RateTooHighFailure",
    "RateTooLowFailure",
    "SolverFailure",
    "SolverResult",
    "Target",
    "TargetDirection",
    "TargetUnreachableFailure",
    "equal_ratio_targets",
    "max_standard_rate",
    "failure_from_violation",
    "solve",
    "speed_bounds",
]
