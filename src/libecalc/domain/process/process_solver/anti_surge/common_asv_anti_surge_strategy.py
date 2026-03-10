from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class CommonASVAntiSurgeStrategy(AntiSurgeStrategy):
    """
    Ensure the train can be propagated at the current speed without going below minimum flow.

    Implementations may adjust control elements (e.g. ASV recirculation, choke) and may
    propagate internally.
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

    def apply(self, inlet_stream: FluidStream) -> bool:
        try:
            self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
            # Already feasible at the current recirculation rate.
            return True
        except RateTooLowError:
            # Below minimum flow: increase recirculation to the minimum feasible rate.
            return self._increase_recirculation_to_minimum_feasible(inlet_stream)

    def _increase_recirculation_to_minimum_feasible(self, inlet_stream: FluidStream) -> bool:
        boundary = self._first_compressor.get_recirculation_range(inlet_stream)

        def recirculation_func(cfg: RecirculationConfiguration) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(cfg.recirculation_rate)
            return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=None,  # capacity only
        )
        solution = solver.solve(recirculation_func)

        self._recirculation_loop.set_recirculation_rate(solution.configuration.recirculation_rate)

        # Optional: make "True" mean "propagation is now feasible"
        try:
            self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
        except RateTooLowError:
            return False

        return solution.success
