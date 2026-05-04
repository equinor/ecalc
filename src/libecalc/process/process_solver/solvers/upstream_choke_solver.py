from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import PRESSURE_CALCULATION_TOLERANCE
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.process.process_solver.solver import Solution, Solver, SolverFailureStatus, TargetNotAchievableEvent


class UpstreamChokeSolver(Solver):
    """Find the upstream ΔP that makes outlet pressure match a target.

    Precondition: unchoked outlet pressure must exceed target (caller guarantees this).
    """

    def __init__(
        self,
        root_finding_strategy: RootFindingStrategy,
        target_pressure: float,
        delta_pressure_boundary: Boundary,
    ):
        self._target_pressure = target_pressure
        self._boundary = delta_pressure_boundary
        self._root_finding_strategy = root_finding_strategy

    def solve(self, func: Callable[[ChokeConfiguration], FluidStream]) -> Solution[ChokeConfiguration]:
        def outlet_pressure(delta_pressure: float) -> float:
            return func(ChokeConfiguration(delta_pressure=delta_pressure)).pressure_bara

        assert outlet_pressure(0) > self._target_pressure

        search_boundary = self._feasible_boundary(func)
        max_pressure = outlet_pressure(search_boundary.max)

        if max_pressure > self._target_pressure:
            return Solution(
                success=False,
                configuration=ChokeConfiguration(delta_pressure=search_boundary.max),
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET,
                    achievable_value=max_pressure,
                    target_value=self._target_pressure,
                ),
            )

        delta_pressure = self._root_finding_strategy.find_root(
            boundary=search_boundary,
            func=lambda x: outlet_pressure(x) - self._target_pressure,
        )
        return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=delta_pressure))

    def _feasible_boundary(self, func: Callable[[ChokeConfiguration], FluidStream]) -> Boundary:
        """Return the search boundary narrowed to the feasible region (no RateTooHighError).

        Probes the upper bound first; if feasible, returns the original boundary immediately.
        Otherwise bisects for the largest ΔP before rate capacity is exceeded.
        """
        try:
            func(ChokeConfiguration(delta_pressure=self._boundary.max))
            return self._boundary
        except RateTooHighError:
            pass

        lo, hi = self._boundary.min, self._boundary.max
        while hi - lo > PRESSURE_CALCULATION_TOLERANCE:
            mid = (lo + hi) / 2
            try:
                func(ChokeConfiguration(delta_pressure=mid))
                lo = mid
            except RateTooHighError:
                hi = mid
        return Boundary(min=self._boundary.min, max=lo)
