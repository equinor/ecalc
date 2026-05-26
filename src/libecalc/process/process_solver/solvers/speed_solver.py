import logging
from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.process.process_solver.solver import (
    Solution,
    Solver,
    TargetDirection,
)

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

    def solve(self, func: Callable[[SpeedConfiguration], FluidStream]) -> Solution[SpeedConfiguration]:
        def get_outlet_stream(speed: float) -> FluidStream:
            return func(SpeedConfiguration(speed=speed))

        max_speed_configuration = SpeedConfiguration(speed=self._boundary.max)
        try:
            maximum_speed_outlet_stream = func(max_speed_configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}", exc_info=e)
            return Solution.from_rate_too_high(e, configuration=max_speed_configuration)
        except RateTooLowError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}", exc_info=e)
            return Solution.from_rate_too_low(e, configuration=max_speed_configuration)

        if maximum_speed_outlet_stream.pressure_bara < self._target_pressure:
            return Solution.target_pressure_unreachable(
                configuration=SpeedConfiguration(self._boundary.max),
                achievable_pressure_bara=maximum_speed_outlet_stream.pressure_bara,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        try:
            minimum_speed_configuration = SpeedConfiguration(speed=self._boundary.min)
            minimum_speed_outlet_stream = func(minimum_speed_configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)

            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            def bool_speed_func(x: float):
                try:
                    get_outlet_stream(speed=x)
                    return False, True
                except RateTooHighError:
                    return True, False
                except RateTooLowError:
                    return False, False

            minimum_speed_within_capacity = self._search_strategy.search(
                boundary=self._boundary,
                func=bool_speed_func,
            )
            minimum_speed_configuration = SpeedConfiguration(speed=minimum_speed_within_capacity)
            minimum_speed_outlet_stream = func(minimum_speed_configuration)

        if minimum_speed_outlet_stream.pressure_bara > self._target_pressure:
            # Solution 2, target pressure is too low
            return Solution.target_pressure_unreachable(
                configuration=minimum_speed_configuration,
                achievable_pressure_bara=minimum_speed_outlet_stream.pressure_bara,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        assert (
            minimum_speed_outlet_stream.pressure_bara
            <= self._target_pressure
            <= maximum_speed_outlet_stream.pressure_bara
        )

        # Solution 1, iterate on speed until target discharge pressure is found
        def root_speed_func(x: float) -> float:
            # We should be able to produce an outlet stream since we adjust minimum speed above,
            # or exit if max speed is not enough
            out = get_outlet_stream(speed=x)
            return out.pressure_bara - self._target_pressure

        speed = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_speed_configuration.speed, max=self._boundary.max),
            func=root_speed_func,
        )
        return Solution(success=True, configuration=SpeedConfiguration(speed=speed))
