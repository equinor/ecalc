import logging
from collections.abc import Callable
from dataclasses import dataclass

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    OutletFluidNotAchievableError,
    RateTooHighError,
    RateTooLowError,
)
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.search_strategies import (
    ACCEPT_AND_GO_HIGHER,
    ACCEPT_AND_GO_LOWER,
    REJECT_AND_GO_HIGHER,
    REJECT_AND_GO_LOWER,
    BinarySearchResult,
    RootFindingStrategy,
    SearchStrategy,
    find_highest_true,
    find_lowest_true,
)
from libecalc.process.process_solver.solver import (
    OutletFluidNotAchievableFailure,
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
        if isinstance(minimum_speed_result, Solution):
            return minimum_speed_result

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
            maximum_speed_result=maximum_speed_result,
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
        except OutletFluidNotAchievableError:
            result = self._highest_speed_with_achievable_outlet(
                get_outlet_stream=lambda speed: func(SpeedConfiguration(speed=speed)),
            )
            if isinstance(result, Solution):
                return result
            return result
        return SpeedResult(configuration=configuration, outlet_stream=outlet_stream)

    def _minimum_speed_result(
        self,
        func: Callable[[SpeedConfiguration], FluidStream],
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> SpeedResult | Solution[SpeedConfiguration]:
        """Evaluate the lower bracket endpoint.

        Returns the outlet stream at minimum speed. If the rate is too high at min speed,
        narrow the lower bound upward to the lowest speed inside capacity and evaluate there.
        If the outlet fluid is not achievable at min speed, narrow upward to the lowest speed
        with an achievable outlet.
        """
        configuration = SpeedConfiguration(speed=self._boundary.min)
        try:
            outlet_stream = func(configuration)
        except RateTooHighError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)
            minimum_speed_within_capacity = self._lowest_speed_within_capacity(get_outlet_stream)
            if isinstance(minimum_speed_within_capacity, Solution):
                return minimum_speed_within_capacity
            configuration = SpeedConfiguration(speed=minimum_speed_within_capacity)
            try:
                outlet_stream = func(configuration)
            except OutletFluidNotAchievableError as eos_error:
                return self._fluid_not_achievable_solution(eos_error, configuration)
        except OutletFluidNotAchievableError:
            result = self._lowest_speed_with_achievable_outlet(get_outlet_stream)
            if isinstance(result, Solution):
                return result
            return result
        return SpeedResult(configuration=configuration, outlet_stream=outlet_stream)

    def _lowest_speed_within_capacity(
        self,
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> float | Solution[SpeedConfiguration]:
        """Lowest speed in [min, max] at which the compressor is not above its maximum flow rate.

        OutletFluidNotAchievableError and RateTooLowError are not capacity-high failures
        and are treated as "within capacity" here; they are handled by other solver phases.

        Returns a Solution only if no speed in the range avoids RateTooHighError.
        """
        last_rate_too_high: RateTooHighError | None = None

        def is_not_rate_too_high(speed: float) -> bool:
            nonlocal last_rate_too_high
            try:
                get_outlet_stream(speed)
                return True
            except RateTooHighError as e:
                last_rate_too_high = e
                return False
            except (OutletFluidNotAchievableError, RateTooLowError):
                return True

        speed = find_lowest_true(is_not_rate_too_high, self._boundary.min, self._boundary.max)
        if speed is not None:
            return speed

        assert last_rate_too_high is not None
        return self._outside_capacity_solution(last_rate_too_high, SpeedConfiguration(speed=self._boundary.max))

    def _highest_speed_with_achievable_outlet(
        self,
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> SpeedResult | Solution[SpeedConfiguration]:
        """Highest speed in [min, max] that produces an achievable outlet stream.

        Called when the maximum speed raises OutletFluidNotAchievableError. Anchors the
        search at the lowest capacity-feasible speed (anything below it raises
        RateTooHighError) and binary-searches upward toward max for the boundary where
        the outlet first becomes unachievable.
        """
        lower_bound = self._lowest_speed_within_capacity(get_outlet_stream)
        if isinstance(lower_bound, Solution):
            return lower_bound

        lower_result = self._speed_result_or_failure(lower_bound, get_outlet_stream)
        if isinstance(lower_result, Solution):
            return lower_result

        def has_achievable_outlet(speed: float) -> BinarySearchResult:
            try:
                get_outlet_stream(speed)
                return ACCEPT_AND_GO_HIGHER
            except (OutletFluidNotAchievableError, RateTooHighError, RateTooLowError):
                return REJECT_AND_GO_LOWER

        speed = self._search_strategy.search(
            boundary=Boundary(min=lower_result.configuration.speed, max=self._boundary.max),
            func=has_achievable_outlet,
        )
        return self._speed_result_or_failure(speed, get_outlet_stream)

    def _lowest_speed_with_achievable_outlet(
        self,
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> SpeedResult | Solution[SpeedConfiguration]:
        """Lowest speed in [min, max] that produces an achievable outlet stream.

        Called when the minimum speed raises OutletFluidNotAchievableError. Anchors the
        search at the highest capacity-feasible speed (anything above it raises
        RateTooLowError) and binary-searches downward toward min for the boundary where
        the outlet first becomes unachievable.
        """
        upper_bound = self._highest_speed_within_capacity(get_outlet_stream)
        if isinstance(upper_bound, Solution):
            return upper_bound

        upper_result = self._speed_result_or_failure(upper_bound, get_outlet_stream)
        if isinstance(upper_result, Solution):
            return upper_result

        def has_achievable_outlet(speed: float) -> BinarySearchResult:
            try:
                get_outlet_stream(speed)
                return ACCEPT_AND_GO_LOWER
            except (OutletFluidNotAchievableError, RateTooHighError, RateTooLowError):
                return REJECT_AND_GO_HIGHER

        speed = self._search_strategy.search(
            boundary=Boundary(min=self._boundary.min, max=upper_result.configuration.speed),
            func=has_achievable_outlet,
        )
        return self._speed_result_or_failure(speed, get_outlet_stream)

    def _highest_speed_within_capacity(
        self,
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> float | Solution[SpeedConfiguration]:
        """Highest speed in [min, max] at which the compressor is not below its minimum flow rate.

        OutletFluidNotAchievableError and RateTooHighError are not capacity-low failures
        and are treated as "within capacity" here; they are handled by other solver phases.

        Returns a Solution only if no speed in the range avoids RateTooLowError.
        """
        last_rate_too_low: RateTooLowError | None = None

        def is_not_rate_too_low(speed: float) -> bool:
            nonlocal last_rate_too_low
            try:
                get_outlet_stream(speed)
                return True
            except RateTooLowError as e:
                last_rate_too_low = e
                return False
            except (OutletFluidNotAchievableError, RateTooHighError):
                return True

        speed = find_highest_true(is_not_rate_too_low, self._boundary.min, self._boundary.max)
        if speed is not None:
            return speed

        assert last_rate_too_low is not None
        return self._outside_capacity_solution(last_rate_too_low, SpeedConfiguration(speed=self._boundary.min))

    def _speed_result_or_failure(
        self,
        speed: float,
        get_outlet_stream: Callable[[float], FluidStream],
    ) -> SpeedResult | Solution[SpeedConfiguration]:
        """Evaluate the outlet stream at `speed`, returning a SpeedResult or a typed failure Solution."""
        configuration = SpeedConfiguration(speed=speed)
        try:
            return SpeedResult(configuration=configuration, outlet_stream=get_outlet_stream(speed))
        except (RateTooHighError, RateTooLowError) as e:
            return self._outside_capacity_solution(e, configuration)
        except OutletFluidNotAchievableError as e:
            return self._fluid_not_achievable_solution(e, configuration)

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
        maximum_speed_result: SpeedResult,
    ) -> Solution[SpeedConfiguration]:
        """Root-find the speed in [min_speed_result.speed, max_speed_result.speed] where outlet pressure equals target.

        If the root finder hits an OutletFluidNotAchievableError mid-iteration, return a typed
        failure Solution at the failing speed.
        """

        def root_speed_func(x: float) -> float:
            out = get_outlet_stream(x)
            return out.pressure_bara - self._target_pressure

        try:
            speed = self._root_finding_strategy.find_root(
                boundary=Boundary(
                    min=minimum_speed_result.configuration.speed,
                    max=maximum_speed_result.configuration.speed,
                ),
                func=root_speed_func,
            )
        except OutletFluidNotAchievableError as e:
            return self._fluid_not_achievable_solution(
                e,
                SpeedConfiguration(speed=e.unachievable_operating_point.speed),
            )
        return Solution(success=True, configuration=SpeedConfiguration(speed=speed))

    def _fluid_not_achievable_solution(
        self,
        e: OutletFluidNotAchievableError,
        configuration: SpeedConfiguration,
    ) -> Solution[SpeedConfiguration]:
        """Translate an OutletFluidNotAchievableError into a failed Solution."""
        logger.warning(f"Outlet fluid not achievable at speed {configuration.speed}", exc_info=e)
        return Solution(
            success=False,
            configuration=configuration,
            failure=OutletFluidNotAchievableFailure(
                source_id=e.process_unit_id,
                unachievable_operating_point=e.unachievable_operating_point,
            ),
        )

    @staticmethod
    def _outside_capacity_solution(
        e: RateTooHighError | RateTooLowError,
        configuration: SpeedConfiguration,
    ) -> Solution[SpeedConfiguration]:
        """Translate a capacity error into a failed Solution."""
        if isinstance(e, RateTooHighError):
            return Solution.from_rate_too_high(e, configuration)
        return Solution.from_rate_too_low(e, configuration)
