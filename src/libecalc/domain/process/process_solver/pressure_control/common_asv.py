from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.recirculation_boundary import (
    get_recirculation_rate_boundary,
)
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class CommonASVPressureControlStrategy(PressureControlStrategy):
    """Varies a single recirculation rate across the entire train to meet target pressure.

    The strategy owns the compressor reference needed to compute the recirculation
    boundary at solve time, since boundary depends on speed which may not be set
    at construction time.
    """

    def __init__(
        self,
        recirculation_loop: RecirculationLoop,
        first_compressor: CompressorStageProcessUnit,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loop = recirculation_loop
        self._first_compressor = first_compressor
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        boundary = get_recirculation_rate_boundary(inlet_stream=inlet_stream, compressor=self._first_compressor)

        def recirculation_func(config: RecirculationConfiguration) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(config.recirculation_rate)
            return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )

        solution = solver.solve(recirculation_func)
        return solution.success
