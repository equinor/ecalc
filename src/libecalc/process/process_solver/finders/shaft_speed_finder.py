import logging
from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.finder import Finder, Finding
from libecalc.process.process_solver.search_strategies import Bisect, BisectResult, RootFindingStrategy
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    RateTooLowFailure,
    TargetDirection,
    TargetPressureUnreachableFailure,
)

logger = logging.getLogger(__name__)


class ShaftSpeedFinder(Finder[SpeedConfiguration]):
    def __init__(
        self,
        search_strategy: Bisect,
        root_finding_strategy: RootFindingStrategy,
        boundary: Boundary,
        target_pressure: float,
    ):
        self._boundary = boundary
        self._target_pressure = target_pressure
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def find(self, func: Callable[[SpeedConfiguration], FluidStream]) -> Finding[SpeedConfiguration]:
        try:
            max_speed_configuration = SpeedConfiguration(speed=self._boundary.max)
            maximum_speed_outlet_stream = func(max_speed_configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}")
            return Finding(configuration=max_speed_configuration, failure=RateTooHighFailure.from_error(e))
        except RateTooLowError as e:
            logger.debug(f"No solution found for maximum speed: {max_speed_configuration}")
            return Finding(configuration=max_speed_configuration, failure=RateTooLowFailure.from_error(e))

        if maximum_speed_outlet_stream.pressure_bara < self._target_pressure:
            return Finding(
                configuration=max_speed_configuration,
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=maximum_speed_outlet_stream.pressure_bara,
                    target_pressure_bara=self._target_pressure,
                    direction=TargetDirection.MAX_BELOW_TARGET,
                ),
            )

        try:
            minimum_speed_configuration, minimum_speed_outlet_stream = self._find_min_within_capacity_speed(func)
        except RateTooLowError as e:
            min_config = SpeedConfiguration(speed=self._boundary.min)
            logger.debug(f"No solution found for minimum speed: {min_config}")
            return Finding(configuration=min_config, failure=RateTooLowFailure.from_error(e))
        except RateTooHighError as e:
            min_config = SpeedConfiguration(speed=self._boundary.min)
            logger.debug(f"No solution found for minimum speed: {min_config}")
            return Finding(configuration=min_config, failure=RateTooHighFailure.from_error(e))

        if minimum_speed_outlet_stream.pressure_bara > self._target_pressure:
            return Finding(
                configuration=minimum_speed_configuration,
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=minimum_speed_outlet_stream.pressure_bara,
                    target_pressure_bara=self._target_pressure,
                    direction=TargetDirection.MIN_ABOVE_TARGET,
                ),
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
        return Finding(configuration=SpeedConfiguration(speed=speed))

    def _find_min_within_capacity_speed(
        self, func: Callable[[SpeedConfiguration], FluidStream]
    ) -> tuple[SpeedConfiguration, FluidStream]:
        """Return the lowest speed configuration within flow capacity, and its outlet stream.

        ``RateTooHighError`` at the boundary minimum is recoverable: higher speed raises the
        stonewall limit; search upward.
        """
        minimum_speed_configuration = SpeedConfiguration(speed=self._boundary.min)
        try:
            minimum_result = func(minimum_speed_configuration)
            return minimum_speed_configuration, minimum_result
        except RateTooHighError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)

            def bool_speed_func(x: float) -> BisectResult:
                try:
                    func(SpeedConfiguration(speed=x))
                    return BisectResult(higher=False, accepted=True)
                except RateTooHighError:
                    return BisectResult(higher=True, accepted=False)
                except RateTooLowError:
                    return BisectResult(higher=False, accepted=False)

            minimum_speed_within_capacity = self._search_strategy.search(
                boundary=self._boundary,
                func=bool_speed_func,
            )
            minimum_speed_configuration = SpeedConfiguration(speed=minimum_speed_within_capacity)
            minimum_result = func(minimum_speed_configuration)
            return minimum_speed_configuration, minimum_result
