from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solution, Solver
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class RecirculationConfiguration:
    recirculation_rate: float

    def __post_init__(self):
        self.recirculation_rate = float(self.recirculation_rate)


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
        boundary = self._recirculation_rate_boundary
        target_pressure = self._target_pressure

        def bool_func(x: float, mode: Literal["minimize", "maximize"]) -> tuple[bool, bool]:
            """
            Return a tuple where first bool is True for higher value,
            the second bool says if the solution is accepted or not:

              - higher=True  => search should move to the right (increase x)
              - accepted=True => x is feasible (within capacity)

            Feasibility is expressed via exceptions from func:
              - RateTooLowError  => x too low, must increase
              - RateTooHighError => x too high, must decrease

            Return a tuple where first bool is True for higher value,
            the second bool says if the solution is accepted or not.

            Need to separate these to avoid accepting a solution which is outside capacity. I.e. when minimizing we
            want to return True for a higher value, but we don't want to accept the solution.
            """
            try:
                func(RecirculationConfiguration(recirculation_rate=x))
                return (False if mode == "minimize" else True), True
            except RateTooLowError:
                return True, False
            except RateTooHighError:
                return False, False

        # ------------------------------------------------------------------
        # 1) Find minimum feasible recirculation rate (capacity lower bound)
        # ------------------------------------------------------------------
        try:
            minimum_rate = boundary.min
            func(RecirculationConfiguration(recirculation_rate=minimum_rate))
            # No error for minimum rate, no need to find min boundary
        except RateTooLowError:
            # Need to increase recirc. First ensure there exists a feasible point in the interval.
            try:
                # If boundary.max is feasible: we know the interval contains a feasible point.
                func(RecirculationConfiguration(recirculation_rate=boundary.max))
                feasible_upper = boundary.max
            except RateTooLowError:
                # Still too low at upper bound => no feasible point in boundary.
                return Solution(
                    success=False, configuration=RecirculationConfiguration(recirculation_rate=boundary.max)
                )
            except RateTooHighError:
                # Upper bound is above max capacity; find a feasible upper point first.
                feasible_upper = self._search_strategy.search(
                    boundary=boundary,
                    func=lambda x: bool_func(x, mode="maximize"),
                )

            # A feasible point now exists in [boundary.min, feasible_upper]. Search for minimum feasible.
            minimum_rate = self._search_strategy.search(
                boundary=Boundary(min=boundary.min, max=feasible_upper),
                func=lambda x: bool_func(x, mode="minimize"),
            )
        except RateTooHighError:
            # Even the minimum bound is above max capacity => no feasible point in boundary.
            return Solution(success=False, configuration=RecirculationConfiguration(recirculation_rate=boundary.min))

        # Capacity-only mode: we are done. Recirculation used only to get within capacity, but not to meet constraints.
        if target_pressure is None:
            return Solution(success=True, configuration=RecirculationConfiguration(recirculation_rate=minimum_rate))

        # ------------------------------------------------------------------
        # 2) Find maximum feasible recirculation rate (capacity upper bound)
        # ------------------------------------------------------------------
        try:
            maximum_rate = boundary.max
            func(RecirculationConfiguration(recirculation_rate=maximum_rate))
            # No error for max rate, no need to find max boundary
        except RateTooHighError:
            # Max boundary is too high. Ensure there exists a feasible point in the interval before searching.
            try:
                func(RecirculationConfiguration(recirculation_rate=boundary.min))
            except RateTooHighError:
                # Still too high at lower bound => no feasible point in boundary.
                return Solution(
                    success=False, configuration=RecirculationConfiguration(recirculation_rate=boundary.min)
                )

            maximum_rate = self._search_strategy.search(
                boundary=boundary,
                func=lambda x: bool_func(x, mode="maximize"),
            )

        # ------------------------------------------------------------------
        # 3) Check if target pressure is reachable within [minimum_rate, maximum_rate]
        # ------------------------------------------------------------------
        minimum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=minimum_rate))
        if minimum_outlet_stream.pressure_bara <= target_pressure.value:
            # Outlet pressure at the minimum feasible recirculation rate is already at or below the target.
            # We return this endpoint as "best effort".
            # success=True only if we are within the configured pressure tolerance, otherwise False.
            success = abs(minimum_outlet_stream.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            return Solution(
                success=success,
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
            )

        maximum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=maximum_rate))
        if maximum_outlet_stream.pressure_bara >= target_pressure.value:
            # Outlet pressure at the maximum feasible recirculation rate is still at or above the target.
            # This means we cannot reach the target pressure within the allowed recirculation range.
            # We return this endpoint as "best effort".
            # success=True only if we are within the configured pressure tolerance.
            success = abs(maximum_outlet_stream.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            return Solution(
                success=success,
                configuration=RecirculationConfiguration(recirculation_rate=maximum_rate),
            )

        # ------------------------------------------------------------------
        # 4) Root finding within feasible interval
        # ------------------------------------------------------------------
        recirculation_rate = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_rate, max=maximum_rate),
            func=lambda x: func(RecirculationConfiguration(recirculation_rate=x)).pressure_bara - target_pressure.value,
        )
        return Solution(success=True, configuration=RecirculationConfiguration(recirculation_rate=recirculation_rate))
