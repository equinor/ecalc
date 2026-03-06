from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class CommonASVPressureControlStrategy(PressureControlStrategy):
    """Varies a single recirculation rate across the entire train to meet target pressure.

    Note: recirculation_rate_boundary must be computed from the same inlet_stream
    that is later passed to apply(). The caller is responsible for this consistency.
    """

    def __init__(
        self,
        recirculation_loop: RecirculationLoop,
        recirculation_rate_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loop = recirculation_loop
        self._recirculation_rate_boundary = recirculation_rate_boundary
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        *,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        def recirculation_func(config: RecirculationConfiguration) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(config.recirculation_rate)
            return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=self._recirculation_rate_boundary,
            target_pressure=target_pressure,
        )

        solution = solver.solve(recirculation_func)
        return solution.success
