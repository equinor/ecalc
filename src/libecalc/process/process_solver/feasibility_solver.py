from collections.abc import Sequence

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_solver import PipelineSolver
from libecalc.process.process_solver.search_strategies import (
    Bisect,
    BisectResult,
    DidNotConvergeError,
)

_RATE_SEARCH_TOLERANCE = 1e-4
_RATE_SEARCH_MAX_ITERATIONS = 40


class FeasibilitySolver:
    """Calculates how much of a given inlet rate exceeds what a compressor train
    can handle for its pressure targets.

    Orchestrates a PipelineSolver (single or multiple sections) and searches for
    the largest feasible inlet rate — the excess is redirected via stream distribution.
    """

    def __init__(
        self,
        pipeline_solver: PipelineSolver | None = None,
        search_strategy: Bisect | None = None,
        *,
        pipeline_section_solver: PipelineSolver | None = None,
    ):
        # pipeline_section_solver is kept for backwards compatibility, use pipeline_solver
        solver = pipeline_solver if pipeline_solver is not None else pipeline_section_solver
        if solver is None or (pipeline_solver is not None and pipeline_section_solver is not None):
            raise ProgrammingError("Exactly one of 'pipeline_solver' and 'pipeline_section_solver' must be given.")
        self._solver: PipelineSolver = solver
        self._search_strategy = search_strategy or Bisect(
            tolerance=_RATE_SEARCH_TOLERANCE,
            max_iterations=_RATE_SEARCH_MAX_ITERATIONS,
        )

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        pressure_targets: Sequence[FloatConstraint],
    ) -> float:
        """Rate [sm³/day] that exceeds what this train can handle.

        This is the amount that must be redirected (e.g. via overflow)
        to another train in the stream distribution.
        """
        full_rate = inlet_stream.standard_rate_sm3_per_day
        if full_rate <= 0.0:
            return 0.0

        if self._is_feasible(inlet_stream, pressure_targets):
            return 0.0

        capacity = self._largest_feasible_rate(inlet_stream, pressure_targets, full_rate)
        return max(0.0, full_rate - capacity)

    def _largest_feasible_rate(
        self,
        inlet_stream: FluidStream,
        pressure_targets: Sequence[FloatConstraint],
        upper_bound_sm3_per_day: float,
    ) -> float:
        boundary = Boundary(min=0.0, max=upper_bound_sm3_per_day)

        def probe(rate: float) -> BisectResult:
            feasible = self._is_feasible(inlet_stream.with_standard_rate(rate), pressure_targets)
            return BisectResult(higher=feasible, accepted=feasible)

        try:
            return self._search_strategy.search(boundary=boundary, func=probe)
        except DidNotConvergeError:
            return 0.0

    def _is_feasible(self, inlet_stream: FluidStream, pressure_targets: Sequence[FloatConstraint]) -> bool:
        return self._solver.find_solution(pressure_targets, inlet_stream).success
