from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import PRESSURE_CALCULATION_TOLERANCE
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.process.process_solver.solver import (
    Solution,
    Solver,
    TargetDirection,
)


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

        # Upstream choking increase the rate (lower pressure, higher volume)
        # If we choke too much, to rate will exceed the capacity / stonewall
        # If so, bisect to the highest ΔP that doesn't exceed stonewall
        stonewall_error: RateTooHighError | None = None
        try:
            outlet_pressure(self._boundary.max)
            search_max = self._boundary.max
        except RateTooHighError as e:
            stonewall_error = e
            lo, hi = self._boundary.min, self._boundary.max
            while hi - lo > PRESSURE_CALCULATION_TOLERANCE:
                mid = (lo + hi) / 2
                try:
                    outlet_pressure(mid)
                    lo = mid
                except RateTooHighError as bisect_error:
                    stonewall_error = bisect_error
                    hi = mid
            search_max = lo

        max_pressure = outlet_pressure(search_max)

        if max_pressure > self._target_pressure:
            if stonewall_error is not None:
                return Solution.from_rate_too_high(
                    stonewall_error,
                    configuration=ChokeConfiguration(delta_pressure=search_max),
                )
            return Solution.target_pressure_unreachable(
                configuration=ChokeConfiguration(delta_pressure=search_max),
                achievable_pressure_bara=max_pressure,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        delta_pressure = self._root_finding_strategy.find_root(
            boundary=Boundary(min=self._boundary.min, max=search_max),
            func=lambda x: outlet_pressure(x) - self._target_pressure,
        )
        return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=delta_pressure))
