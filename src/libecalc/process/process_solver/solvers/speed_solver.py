import logging
from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver import solver_debug
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

    def solve(self, func1: Callable[[SpeedConfiguration], FluidStream]) -> Solution[SpeedConfiguration]:
        if solver_debug.is_enabled():
            original_func = func1

            def func(cfg: SpeedConfiguration) -> FluidStream:
                try:
                    result = original_func(cfg)
                    solver_debug.emit(
                        "speed.probe",
                        speed=cfg.speed,
                        pressure=result.pressure_bara,
                        phase=solver_debug.current_phase(),
                        result="ok",
                    )
                    return result
                except RateTooHighError:
                    solver_debug.emit(
                        "speed.probe",
                        speed=cfg.speed,
                        pressure=None,
                        phase=solver_debug.current_phase(),
                        result="too_high",
                    )
                    raise
                except RateTooLowError:
                    solver_debug.emit(
                        "speed.probe",
                        speed=cfg.speed,
                        pressure=None,
                        phase=solver_debug.current_phase(),
                        result="too_low",
                    )
                    raise

        try:
            max_speed_configuration = SpeedConfiguration(speed=self._boundary.max)
            maximum_speed_outlet_stream = func1(max_speed_configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}")
            return Solution.from_rate_too_high(e, configuration=max_speed_configuration)
        except RateTooLowError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}")
            return Solution.from_rate_too_low(e, configuration=max_speed_configuration)

        if maximum_speed_outlet_stream.pressure_bara < self._target_pressure:
            return Solution.target_pressure_unreachable(
                configuration=SpeedConfiguration(self._boundary.max),
                achievable_pressure_bara=maximum_speed_outlet_stream.pressure_bara,
                target_pressure_bara=self._target_pressure,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        minimum_speed_configuration, minimum_speed_outlet_stream = self._find_min_within_capacity_speed(func1)

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
            out = func(SpeedConfiguration(speed=x))
            return out.pressure_bara - self._target_pressure

        speed = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_speed_configuration.speed, max=self._boundary.max),
            func=root_speed_func,
        )
        return Solution(success=True, configuration=SpeedConfiguration(speed=speed))

    def _find_min_within_capacity_speed(
        self, func: Callable[[SpeedConfiguration], FluidStream]
    ) -> tuple[SpeedConfiguration, FluidStream]:
        """Return the lowest speed configuration within flow capacity, and its outlet stream.

        ``RateTooHighError`` at the boundary minimum is recoverable: higher speed raises the
        stonewall limit; search upward.
        """
        minimum_speed_configuration = SpeedConfiguration(speed=self._boundary.min)
        try:
            return minimum_speed_configuration, func(minimum_speed_configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)

            def bool_speed_func(x: float) -> tuple[bool, bool]:
                try:
                    func(SpeedConfiguration(speed=x))
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
            return minimum_speed_configuration, func(minimum_speed_configuration)
