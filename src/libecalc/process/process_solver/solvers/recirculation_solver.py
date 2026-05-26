from typing import Literal

from libecalc.process.process_pipeline.propagation_failure import (
    PropagationFailure,
    RateTooHigh,
    RateTooLow,
    TargetDirection,
    TargetPressureUnreachable,
)
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.process.process_solver.solver import InfeasibleDuringSearch, PropagationCallback, Solution, Solver


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

    def solve(self, func: PropagationCallback[RecirculationConfiguration]) -> Solution[RecirculationConfiguration]:
        def bool_func(x: float, mode: Literal["minimize", "maximize"]) -> tuple[bool, bool]:
            """
            Return a tuple where first bool is True for higher value,
            the second bool says if the solution is accepted or not.

            Need to separate these to avoid accepting a solution which is outside capacity. I.e. when minimizing we
            want to return True for a higher value, but we don't want to accept the solution.
            """
            result = func(RecirculationConfiguration(recirculation_rate=x))
            if isinstance(result, RateTooLow):
                return True, False
            if isinstance(result, RateTooHigh):
                return False, False
            # FluidStream (or any other PropagationFailure: treat as valid sample)
            return (False if mode == "minimize" else True), True

        minimum_rate = self._recirculation_rate_boundary.min
        minimum_result = func(RecirculationConfiguration(recirculation_rate=minimum_rate))
        if isinstance(minimum_result, RateTooLow):
            # Min boundary is too low, find solution
            minimum_rate = self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: bool_func(x, mode="minimize"),
            )
        elif isinstance(minimum_result, RateTooHigh):
            # Flow is above stonewall at zero recirculation; adding recirculation cannot help.
            return Solution.failed(
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=minimum_result,
            )
        elif isinstance(minimum_result, PropagationFailure):
            return Solution.failed(
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=minimum_result,
            )

        target_pressure = self._target_pressure
        if target_pressure is None:
            # Recirc used to get within capacity, but not to meet constraints
            return Solution(success=True, configuration=RecirculationConfiguration(recirculation_rate=minimum_rate))

        maximum_rate = self._recirculation_rate_boundary.max
        maximum_result = func(RecirculationConfiguration(recirculation_rate=maximum_rate))
        if isinstance(maximum_result, RateTooHigh):
            # Max boundary is too high, find solution
            maximum_rate = self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: bool_func(x, mode="maximize"),
            )

        minimum_outlet = func(RecirculationConfiguration(recirculation_rate=minimum_rate))
        if isinstance(minimum_outlet, PropagationFailure):
            return Solution.failed(
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=minimum_outlet,
            )
        if minimum_outlet.pressure_bara <= target_pressure:
            # Highest possible pressure is too low
            is_success = minimum_outlet.pressure_bara == target_pressure
            return Solution(
                success=is_success,
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=None
                if is_success
                else TargetPressureUnreachable(
                    achievable_pressure_bara=minimum_outlet.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MAX_BELOW_TARGET,
                ),
            )
        maximum_outlet = func(RecirculationConfiguration(recirculation_rate=maximum_rate))
        if isinstance(maximum_outlet, PropagationFailure):
            return Solution.failed(
                configuration=RecirculationConfiguration(recirculation_rate=maximum_rate),
                failure=maximum_outlet,
            )
        if maximum_outlet.pressure_bara >= target_pressure:
            # Lowest possible pressure is too high
            is_success = maximum_outlet.pressure_bara == self._target_pressure
            return Solution(
                success=is_success,
                configuration=RecirculationConfiguration(recirculation_rate=maximum_rate),
                failure=None
                if is_success
                else TargetPressureUnreachable(
                    achievable_pressure_bara=maximum_outlet.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MIN_ABOVE_TARGET,
                ),
            )

        def root_func(x: float) -> float:
            result = func(RecirculationConfiguration(recirculation_rate=x))
            if isinstance(result, PropagationFailure):
                raise InfeasibleDuringSearch(result)
            return result.pressure_bara - target_pressure.value

        try:
            recirculation_rate = self._root_finding_strategy.find_root(
                boundary=Boundary(min=minimum_rate, max=maximum_rate),
                func=root_func,
            )
        except InfeasibleDuringSearch as exc:
            return Solution.failed(
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=exc.failure,
            )
        return Solution(success=True, configuration=RecirculationConfiguration(recirculation_rate=recirculation_rate))
