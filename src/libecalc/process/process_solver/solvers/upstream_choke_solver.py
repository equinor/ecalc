from libecalc.domain.process.compressor.core.train.utils.common import PRESSURE_CALCULATION_TOLERANCE
from libecalc.process.process_pipeline.propagation_failure import (
    DidNotConverge,
    PropagationFailure,
    RateTooHigh,
    TargetDirection,
)
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.process.process_solver.solver import InfeasibleDuringSearch, PropagationCallback, Solution, Solver


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

    def solve(self, func: PropagationCallback[ChokeConfiguration]) -> Solution[ChokeConfiguration]:
        def outlet_pressure(delta_pressure: float) -> float:
            result = func(ChokeConfiguration(delta_pressure=delta_pressure))
            if isinstance(result, PropagationFailure):
                raise InfeasibleDuringSearch(result)
            return result.pressure_bara

        try:
            unchoked = outlet_pressure(0)
        except InfeasibleDuringSearch as exc:
            return Solution.failed(configuration=ChokeConfiguration(delta_pressure=0), failure=exc.failure)
        assert unchoked > self._target_pressure

        search_boundary = self._feasible_boundary(func)
        try:
            max_pressure = outlet_pressure(search_boundary.max)
        except InfeasibleDuringSearch as exc:
            return Solution.failed(
                configuration=ChokeConfiguration(delta_pressure=search_boundary.max),
                failure=exc.failure,
            )

        if max_pressure > self._target_pressure:
            return Solution.target_pressure_unreachable(
                configuration=ChokeConfiguration(delta_pressure=search_boundary.max),
                achievable_pressure_bara=max_pressure,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        try:
            delta_pressure = self._root_finding_strategy.find_root(
                boundary=search_boundary,
                func=lambda x: outlet_pressure(x) - self._target_pressure,
            )
        except InfeasibleDuringSearch as exc:
            return Solution.failed(
                configuration=ChokeConfiguration(delta_pressure=search_boundary.min),
                failure=exc.failure,
            )
        if isinstance(delta_pressure, DidNotConverge):
            return Solution.failed(
                configuration=ChokeConfiguration(delta_pressure=search_boundary.min),
                failure=delta_pressure,
            )
        return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=delta_pressure))

    def _feasible_boundary(self, func: PropagationCallback[ChokeConfiguration]) -> Boundary:
        """Return the search boundary narrowed to the feasible region (no RateTooHigh).

        Probes the upper bound first; if feasible, returns the original boundary immediately.
        Otherwise bisects for the largest ΔP before rate capacity is exceeded.
        """
        if not isinstance(func(ChokeConfiguration(delta_pressure=self._boundary.max)), RateTooHigh):
            return self._boundary

        lo, hi = self._boundary.min, self._boundary.max
        while hi - lo > PRESSURE_CALCULATION_TOLERANCE:
            mid = (lo + hi) / 2
            if isinstance(func(ChokeConfiguration(delta_pressure=mid)), RateTooHigh):
                hi = mid
            else:
                lo = mid
        return Boundary(min=self._boundary.min, max=lo)
