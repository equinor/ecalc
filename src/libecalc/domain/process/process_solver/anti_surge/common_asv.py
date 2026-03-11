from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class CommonASVAntiSurgeStrategy(AntiSurgeStrategy):
    """
    Ensure the train can be propagated at the current speed without going below minimum flow.

    This strategy is used during speed search when the train cannot be propagated with
    recirculation=0 because one or more stages fall below minimum flow (RateTooLowError).

    Contract:
      - Mutates the recirculation loop by setting a recirculation rate.
      - Returns the resulting outlet stream for the current speed.
    """

    def __init__(
        self,
        *,
        recirculation_loop: RecirculationLoop,
        first_compressor: CompressorStageProcessUnit,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loop = recirculation_loop
        self._first_compressor = first_compressor
        self._root_finding_strategy = root_finding_strategy

    def apply(self, inlet_stream: FluidStream) -> FluidStream:
        # Increase recirculation to give minimum feasible flow and return outlet.
        recirculation_rate = self._increase_recirculation_to_minimum_feasible(inlet_stream)
        self._recirculation_loop.set_recirculation_rate(recirculation_rate)
        return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    def _increase_recirculation_to_minimum_feasible(self, inlet_stream: FluidStream) -> float:
        # The recirculation boundary depends on the inlet stream (and implicitly current speed).
        boundary = self._first_compressor.get_recirculation_range(inlet_stream)

        def recirculation_func(cfg: RecirculationConfiguration) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(cfg.recirculation_rate)
            return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        # target_pressure=None means: "solve only for within-capacity feasibility",
        # not for meeting any pressure constraint.
        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=None,  # capacity only
        )
        solution = solver.solve(recirculation_func)

        return solution.configuration.recirculation_rate
