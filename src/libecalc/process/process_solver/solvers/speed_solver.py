import logging
from collections.abc import Callable
from dataclasses import dataclass

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.search_strategies import (
    ACCEPT_AND_GO_LOWER,
    REJECT_AND_GO_HIGHER,
    REJECT_AND_GO_LOWER,
    BinarySearchResult,
    RootFindingStrategy,
    SearchStrategy,
)
from libecalc.process.process_solver.solver import (
    Solution,
    Solver,
    TargetDirection,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeedResult:
    configuration: SpeedConfiguration
    outlet_stream: FluidStream


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
        """Find the speed at which `func` produces an outlet stream matching the target pressure.

        Phases:
          1. Evaluate the max-speed endpoint. If it cannot reach the target, fail target-not-achievable.
          2. Evaluate the min-speed endpoint (or its capacity-feasible replacement). If it overshoots
             the target, fail target-not-achievable.
          3. Root-find on speed within the [min, max] bracket so that outlet pressure equals the target.
        """

        def get_outlet_stream(speed: float) -> FluidStream:
            return func(SpeedConfiguration(speed=speed))

        maximum_speed_result = self._maximum_speed_result(func)
        if isinstance(maximum_speed_result, Solution):
            return maximum_speed_result

        if maximum_speed_result.outlet_stream.pressure_bara < self._target_pressure:
            return self._target_not_achievable_at_maximum_speed(maximum_speed_result)

        minimum_speed_result = self._minimum_speed_result(func, get_outlet_stream)

        if minimum_speed_result.outlet_stream.pressure_bara > self._target_pressure:
            return self._target_not_achievable_at_minimum_speed(minimum_speed_result)

        assert (
            minimum_speed_result.outlet_stream.pressure_bara
            <= self._target_pressure
            <= maximum_speed_result.outlet_stream.pressure_bara
        )

        return self._solve_within_pressure_bracket(
            get_outlet_stream=get_outlet_stream,
            minimum_speed_result=minimum_speed_result,
        )

    def _maximum_speed_result(
        self,
        func: Callable[[SpeedConfiguration], FluidStream],
    ) -> SpeedResult | Solution[SpeedConfiguration]:
        """Evaluate the upper bracket endpoint.

        Returns the outlet stream at maximum speed, or an outside-capacity Solution if
        that speed is outside the compressor's flow range.
        """
        configuration = SpeedConfiguration(speed=self._boundary.max)
        try:
            outlet_stream = func(configuration)
        except (RateTooHighError, RateTooLowError) as e:
            logger.debug(f"No solution found for maximum speed: {configuration}", exc_info=e)
            return self._outside_capacity_solution(e, configuration)
        return SpeedResult(configuration=configuration, outlet_stream=outlet_stream)

    def _minimum_speed_result(
        self,
        func: Callable[[SpeedConfiguration], FluidStream],
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> SpeedResult:
        """Evaluate the lower bracket endpoint.

        Returns the outlet stream at minimum speed. If the rate is too high at min speed,
        narrow the lower bound upward to the lowest speed inside capacity and evaluate there.
        """
        configuration = SpeedConfiguration(speed=self._boundary.min)
        try:
            outlet_stream = func(configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)
            minimum_speed_within_capacity = self._lowest_speed_within_capacity(get_outlet_stream)
            configuration = SpeedConfiguration(speed=minimum_speed_within_capacity)
            outlet_stream = func(configuration)
        return SpeedResult(configuration=configuration, outlet_stream=outlet_stream)

    def _lowest_speed_within_capacity(self, get_outlet_stream: Callable[[float], FluidStream]) -> float:
        """Lowest speed in [min, max] at which the compressor is not above its maximum flow rate."""

        def capacity_search(x: float) -> BinarySearchResult:
            try:
                get_outlet_stream(x)
                return ACCEPT_AND_GO_LOWER
            except RateTooHighError:
                return REJECT_AND_GO_HIGHER
            except RateTooLowError:
                return REJECT_AND_GO_LOWER

        return self._search_strategy.search(
            boundary=self._boundary,
            func=capacity_search,
        )

    def _target_not_achievable_at_maximum_speed(self, result: SpeedResult) -> Solution[SpeedConfiguration]:
        """Build a failure Solution: max-speed outlet pressure is below the target."""
        return Solution.target_pressure_unreachable(
            configuration=result.configuration,
            achievable_pressure_bara=result.outlet_stream.pressure_bara,
            target_pressure_bara=self._target_pressure,
            direction=TargetDirection.MAX_BELOW_TARGET,
        )

    def _target_not_achievable_at_minimum_speed(self, result: SpeedResult) -> Solution[SpeedConfiguration]:
        """Build a failure Solution: min-speed outlet pressure is above the target."""
        return Solution.target_pressure_unreachable(
            configuration=result.configuration,
            achievable_pressure_bara=result.outlet_stream.pressure_bara,
            target_pressure_bara=self._target_pressure,
            direction=TargetDirection.MIN_ABOVE_TARGET,
        )

    def _solve_within_pressure_bracket(
        self,
        get_outlet_stream: Callable[[float], FluidStream],
        minimum_speed_result: SpeedResult,
    ) -> Solution[SpeedConfiguration]:
        """Root-find the speed in [min_speed_result.speed, max] where outlet pressure equals target."""

        def root_speed_func(x: float) -> float:
            out = get_outlet_stream(x)
            return out.pressure_bara - self._target_pressure

        speed = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_speed_result.configuration.speed, max=self._boundary.max),
            func=root_speed_func,
        )
        return Solution(success=True, configuration=SpeedConfiguration(speed=speed))

    @staticmethod
    def _outside_capacity_solution(
        e: RateTooHighError | RateTooLowError,
        configuration: SpeedConfiguration,
    ) -> Solution[SpeedConfiguration]:
        """Translate a capacity error into a failed Solution."""
        if isinstance(e, RateTooHighError):
            return Solution.from_rate_too_high(e, configuration)
        return Solution.from_rate_too_low(e, configuration)
