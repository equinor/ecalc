from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import Solution
from libecalc.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.process.process_units.compressor import Compressor


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
        simulator: ProcessRunner,
        recirculation_loop_id: ConfigurationHandlerId,
        first_compressor: Compressor,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loop_id = recirculation_loop_id
        self._first_compressor = first_compressor
        self._root_finding_strategy = root_finding_strategy
        self._simulator = simulator

    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        # Increase recirculation to give minimum feasible flow and return outlet.
        recirculation_solution = self._increase_recirculation_to_minimum_feasible(inlet_stream)
        return Solution(
            success=recirculation_solution.success,
            configuration=[
                Configuration(
                    configuration_handler_id=self._recirculation_loop_id,
                    value=recirculation_solution.configuration,
                )
            ],
        )

    def _apply_configuration(self, cfg: RecirculationConfiguration):
        self._simulator.apply_configuration(
            Configuration(configuration_handler_id=self._recirculation_loop_id, value=cfg)
        )

    def _increase_recirculation_to_minimum_feasible(
        self, inlet_stream: FluidStream
    ) -> Solution[RecirculationConfiguration]:
        # The recirculation boundary depends on the inlet stream (and implicitly current speed).
        compressor_inlet_stream = self._simulator.run(inlet_stream=inlet_stream, to_id=self._first_compressor.get_id())
        boundary = self._first_compressor.get_recirculation_range(compressor_inlet_stream)

        def recirculation_func(cfg: RecirculationConfiguration) -> FluidStream:
            self._apply_configuration(cfg)
            return self._simulator.run(inlet_stream=inlet_stream)

        # target_pressure=None means: "solve only for within-capacity feasibility",
        # not for meeting any pressure constraint.
        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=None,  # capacity only
        )
        solution = solver.solve(recirculation_func)

        return solution
