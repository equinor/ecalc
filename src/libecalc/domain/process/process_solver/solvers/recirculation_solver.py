from typing import Literal

from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class RecirculationSolver(Solver):
    def __init__(
        self,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        recirculation_loop: RecirculationLoop,
        recirculation_rate_boundary: Boundary,
        target_pressure: float | None = None,
    ):
        self._recirculation_loop = recirculation_loop
        self._recirculation_rate_boundary = recirculation_rate_boundary
        self._target_pressure = target_pressure
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        def get_outlet_stream(recirculation_rate: float) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(recirculation_rate)
            return process_system.propagate_stream(inlet_stream=inlet_stream)

        def bool_func(x: float, mode: Literal["minimize", "maximize"]) -> tuple[bool, bool]:
            """
            Return a tuple where first bool is True for higher value,
            the second bool says if the solution is accepted or not.

            Need to separate these to avoid accepting a solution which is outside capacity. I.e. when minimizing we
            want to return True for a higher value, but we don't want to accept the solution.
            """
            try:
                get_outlet_stream(x)
                return False if mode == "minimize" else True, True
            except RateTooLowError:
                return True, False
            except RateTooHighError:
                return False, False

        try:
            minimum_rate = self._recirculation_rate_boundary.min
            get_outlet_stream(recirculation_rate=minimum_rate)
            # No error for minimum rate, no need to find min boundary
        except RateTooLowError:
            # Min boundary is too low, find solution
            minimum_rate = self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: bool_func(x, mode="minimize"),
            )

        target_pressure = self._target_pressure
        if target_pressure is None:
            # Recirc used to get within capacity, but not to meet constraints
            return get_outlet_stream(minimum_rate)

        try:
            maximum_rate = self._recirculation_rate_boundary.max
            get_outlet_stream(recirculation_rate=maximum_rate)
            # No error for max rate, no need to find max boundary
        except RateTooHighError:
            # Max boundary is too high, find solution
            maximum_rate = self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: bool_func(x, mode="maximize"),
            )

        minimum_outlet_stream = get_outlet_stream(recirculation_rate=minimum_rate)
        if minimum_outlet_stream.pressure_bara <= target_pressure:
            # Highest possible pressure is too low
            return minimum_outlet_stream

        maximum_outlet_stream = get_outlet_stream(recirculation_rate=maximum_rate)
        if maximum_outlet_stream.pressure_bara >= target_pressure:
            # Lowest possible pressure is too high
            return maximum_outlet_stream

        recirculation_rate = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_rate, max=maximum_rate),
            func=lambda x: get_outlet_stream(recirculation_rate=x).pressure_bara - target_pressure,
        )
        return get_outlet_stream(recirculation_rate=recirculation_rate)
