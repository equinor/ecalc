import logging

from libecalc.process.process_pipeline.propagation_failure import (
    PropagationFailure,
    RateTooHigh,
    RateTooLow,
    TargetDirection,
)
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.process.process_solver.solver import InfeasibleDuringSearch, PropagationCallback, Solution, Solver

logger = logging.getLogger(__name__)


class SpeedSolver(Solver[SpeedConfiguration]):
    def __init__(
        self,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        boundary: Boundary,
        target_pressure: float,
    ):
        self._boundary = boundary
        self._target_pressure = target_pressure
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def solve(self, func: PropagationCallback[SpeedConfiguration]) -> Solution[SpeedConfiguration]:
        max_speed_configuration = SpeedConfiguration(speed=self._boundary.max)
        maximum_speed_outlet = func(max_speed_configuration)
        if isinstance(maximum_speed_outlet, PropagationFailure):
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration} ({maximum_speed_outlet})")
            return Solution.failed(configuration=max_speed_configuration, failure=maximum_speed_outlet)

        if maximum_speed_outlet.pressure_bara < self._target_pressure:
            return Solution.target_pressure_unreachable(
                configuration=SpeedConfiguration(self._boundary.max),
                achievable_pressure_bara=maximum_speed_outlet.pressure_bara,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        minimum_speed_configuration = SpeedConfiguration(speed=self._boundary.min)
        minimum_speed_outlet = func(minimum_speed_configuration)
        if isinstance(minimum_speed_outlet, RateTooHigh):
            logger.debug(f"Rate too high at minimum speed: {self._boundary.min}")

            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            def bool_speed_func(x: float) -> tuple[bool, bool]:
                result = func(SpeedConfiguration(speed=x))
                if isinstance(result, RateTooHigh):
                    return True, False
                if isinstance(result, RateTooLow):
                    return False, False
                # FluidStream or any other PropagationFailure: treat as valid sample
                return False, True

            minimum_speed_within_capacity = self._search_strategy.search(
                boundary=self._boundary,
                func=bool_speed_func,
            )
            minimum_speed_configuration = SpeedConfiguration(speed=minimum_speed_within_capacity)
            minimum_speed_outlet = func(minimum_speed_configuration)
            if isinstance(minimum_speed_outlet, PropagationFailure):
                logger.debug(f"No solution after narrowing minimum speed: {minimum_speed_outlet}")
                return Solution.failed(configuration=minimum_speed_configuration, failure=minimum_speed_outlet)
        elif isinstance(minimum_speed_outlet, PropagationFailure):
            logger.debug(f"No solution found for minimum speed: {minimum_speed_outlet}")
            return Solution.failed(configuration=minimum_speed_configuration, failure=minimum_speed_outlet)

        if minimum_speed_outlet.pressure_bara > self._target_pressure:
            # Solution 2, target pressure is too low
            return Solution.target_pressure_unreachable(
                configuration=minimum_speed_configuration,
                achievable_pressure_bara=minimum_speed_outlet.pressure_bara,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        assert minimum_speed_outlet.pressure_bara <= self._target_pressure <= maximum_speed_outlet.pressure_bara

        # Solution 1, iterate on speed until target discharge pressure is found
        def root_speed_func(x: float) -> float:
            # We should be able to produce an outlet stream since we adjust minimum speed above,
            # or exit if max speed is not enough — but capacity boundaries can still be hit between
            # the probed speeds, so propagate any failure out via InfeasibleDuringSearch.
            out = func(SpeedConfiguration(speed=x))
            if isinstance(out, PropagationFailure):
                raise InfeasibleDuringSearch(out)
            return out.pressure_bara - self._target_pressure

        try:
            speed = self._root_finding_strategy.find_root(
                boundary=Boundary(min=minimum_speed_configuration.speed, max=self._boundary.max),
                func=root_speed_func,
            )
        except InfeasibleDuringSearch as exc:
            return Solution.failed(configuration=minimum_speed_configuration, failure=exc.failure)
        return Solution(success=True, configuration=SpeedConfiguration(speed=speed))
