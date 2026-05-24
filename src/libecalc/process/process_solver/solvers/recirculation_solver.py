from collections.abc import Callable
from typing import Literal

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    InfeasiblePressureError,
    RateTooHighError,
    RateTooLowError,
)
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.process.process_solver.solver import (
    InfeasiblePressureFailure,
    RateTooHighFailure,
    Solution,
    Solver,
    TargetDirection,
    TargetPressureUnreachableFailure,
)


class RecirculationSolver(Solver):
    def __init__(
        self,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        recirculation_rate_boundary: Boundary,
        target_pressure: FloatConstraint | None = None,
    ):
        self._recirculation_rate_boundary = recirculation_rate_boundary
        self._target_pressure = target_pressure
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def solve(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> Solution[RecirculationConfiguration]:
        try:
            minimum_rate = self._find_min_within_capacity_rate(func)

            target_pressure = self._target_pressure
            if target_pressure is None:
                # Recirc used to get within capacity, but not to meet constraints
                return Solution(success=True, configuration=RecirculationConfiguration(recirculation_rate=minimum_rate))

            maximum_rate = self._find_max_within_capacity_rate(func)

            minimum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=minimum_rate))
            if minimum_outlet_stream.pressure_bara <= target_pressure:
                # Highest possible pressure is too low
                is_success = minimum_outlet_stream.pressure_bara == target_pressure
                return Solution(
                    success=is_success,
                    configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                    failure=None
                    if is_success
                    else TargetPressureUnreachableFailure(
                        achievable_pressure_bara=minimum_outlet_stream.pressure_bara,
                        target_pressure_bara=target_pressure.value,
                        direction=TargetDirection.MAX_BELOW_TARGET,
                    ),
                )
            maximum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=maximum_rate))
            if maximum_outlet_stream.pressure_bara >= target_pressure:
                # Lowest possible pressure is too high
                is_success = maximum_outlet_stream.pressure_bara == self._target_pressure
                return Solution(
                    success=is_success,
                    configuration=RecirculationConfiguration(recirculation_rate=maximum_rate),
                    failure=None
                    if is_success
                    else TargetPressureUnreachableFailure(
                        achievable_pressure_bara=maximum_outlet_stream.pressure_bara,
                        target_pressure_bara=target_pressure.value,
                        direction=TargetDirection.MIN_ABOVE_TARGET,
                    ),
                )

            recirculation_rate = self._root_finding_strategy.find_root(
                boundary=Boundary(min=minimum_rate, max=maximum_rate),
                func=lambda x: (
                    func(RecirculationConfiguration(recirculation_rate=x)).pressure_bara - target_pressure.value
                ),
            )
            return Solution(
                success=True, configuration=RecirculationConfiguration(recirculation_rate=recirculation_rate)
            )
        except RateTooHighError as e:
            # Flow is above stonewall at zero recirculation; adding recirculation cannot help.
            return Solution(
                success=False,
                configuration=RecirculationConfiguration(recirculation_rate=self._recirculation_rate_boundary.min),
                failure=RateTooHighFailure.from_error(e),
            )
        except InfeasiblePressureError as e:
            return Solution(
                success=False,
                configuration=RecirculationConfiguration(recirculation_rate=self._recirculation_rate_boundary.min),
                failure=InfeasiblePressureFailure.from_error(e),
            )

    def _find_min_within_capacity_rate(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> float:
        """Return the smallest recirculation rate that keeps every stage within flow capacity.

        ``RateTooLowError`` at the boundary minimum is recoverable (more recirculation adds
        flow); ``RateTooHighError`` is not (more recirculation only adds more flow) and
        propagates.
        """
        minimum_rate = self._recirculation_rate_boundary.min
        try:
            func(RecirculationConfiguration(recirculation_rate=minimum_rate))
            return minimum_rate
        except RateTooLowError:
            return self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: self._bool_func(func, x, mode="minimize"),
            )

    def _find_max_within_capacity_rate(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> float:
        """Return the largest recirculation rate that keeps every stage within flow capacity.

        ``RateTooHighError`` at the boundary maximum is recoverable: search downward.
        """
        maximum_rate = self._recirculation_rate_boundary.max
        try:
            func(RecirculationConfiguration(recirculation_rate=maximum_rate))
            return maximum_rate
        except RateTooHighError:
            return self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: self._bool_func(func, x, mode="maximize"),
            )

    @staticmethod
    def _bool_func(
        func: Callable[[RecirculationConfiguration], FluidStream],
        x: float,
        mode: Literal["minimize", "maximize"],
    ) -> tuple[bool, bool]:
        """Probe a candidate rate for the search strategy.

        Returns ``(is_higher, is_accepted)``. The two booleans are decoupled so an
        out-of-capacity candidate can never be accepted as a solution.
        """
        try:
            func(RecirculationConfiguration(recirculation_rate=x))
            return False if mode == "minimize" else True, True
        except RateTooLowError:
            return True, False
        except RateTooHighError:
            return False, False
