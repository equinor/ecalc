from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import OutsideCapacityError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.search_strategies import (
    BinarySearchStrategy,
    DidNotConvergeError,
    SearchStrategy,
)

_RATE_SEARCH_TOLERANCE = 1e-4
_RATE_SEARCH_MAX_ITERATIONS = 40


class FeasibilitySolver:
    """Calculates how much of a given inlet rate exceeds what a compressor train
    can handle for a target pressure.

    Orchestrates OutletPressureSolver and queries compressor charts to find
    the feasible rate — the excess is redirected via stream distribution.
    """

    def __init__(
        self,
        outlet_pressure_solver: OutletPressureSolver,
        search_strategy: SearchStrategy | None = None,
    ):
        self._solver = outlet_pressure_solver
        self._search_strategy = search_strategy or BinarySearchStrategy(
            tolerance=_RATE_SEARCH_TOLERANCE,
            max_iterations=_RATE_SEARCH_MAX_ITERATIONS,
        )

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        """Rate [sm³/day] that exceeds what this train can handle.

        This is the amount that must be redirected (e.g. via overflow)
        to another train in the stream distribution.
        """
        full_rate = inlet_stream.standard_rate_sm3_per_day
        if full_rate <= 0.0:
            return 0.0

        if self._is_feasible(inlet_stream, target_pressure):
            return 0.0

        capacity = self._largest_feasible_rate(inlet_stream, target_pressure, full_rate)
        return max(0.0, full_rate - capacity)

    def _largest_feasible_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
        upper_bound_sm3_per_day: float,
    ) -> float:
        boundary = Boundary(min=0.0, max=upper_bound_sm3_per_day)
        try:
            return self._search_strategy.search(
                boundary=boundary,
                func=lambda rate: (
                    self._is_feasible(inlet_stream.with_standard_rate(rate), target_pressure),
                    True,
                ),
            )
        except DidNotConvergeError:
            return 0.0

    def _is_feasible(self, inlet_stream: FluidStream, target_pressure: FloatConstraint) -> bool:
        try:
            return self._solver.find_solution(target_pressure, inlet_stream).success
        except (DidNotConvergeError, OutsideCapacityError):
            return False
