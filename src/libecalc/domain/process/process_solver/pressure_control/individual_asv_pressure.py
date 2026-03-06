from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import (
    BoundaryFactory,
    PressureControlStrategy,
)
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVPressureControlStrategy(PressureControlStrategy):
    """Varies recirculation rate independently per stage to meet equal pressure ratio.

    Boundary for each stage is computed lazily from the stage's actual inlet stream,
    which is only known after the previous stage has been solved.
    """

    def __init__(
        self,
        recirculation_loops: list[RecirculationLoop],
        get_boundary_for_stage: BoundaryFactory,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loops = recirculation_loops
        self._get_boundary_for_stage = get_boundary_for_stage
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        *,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        n_stages = len(self._recirculation_loops)
        pressure_ratio_per_stage = (target_pressure.value / inlet_stream.pressure_bara) ** (1.0 / n_stages)

        current_stream = inlet_stream
        for i, loop in enumerate(self._recirculation_loops):
            # Target pressure for this stage: cumulative from original inlet
            stage_target_pressure = inlet_stream.pressure_bara * (pressure_ratio_per_stage ** (i + 1))

            # Boundary computed from actual inlet stream to this stage
            boundary = self._get_boundary_for_stage(i, current_stream)

            def recirculation_func(config, _loop=loop, _stream=current_stream):
                _loop.set_recirculation_rate(config.recirculation_rate)
                return _loop.propagate_stream(inlet_stream=_stream)

            solver = RecirculationSolver(
                search_strategy=BinarySearchStrategy(tolerance=10e-3),
                root_finding_strategy=self._root_finding_strategy,
                recirculation_rate_boundary=boundary,
                target_pressure=FloatConstraint(stage_target_pressure),
            )

            solution = solver.solve(recirculation_func)
            if not solution.success:
                return False

            # Propagate to get inlet stream for next stage
            loop.set_recirculation_rate(solution.configuration.recirculation_rate)
            current_stream = loop.propagate_stream(inlet_stream=current_stream)

        return True
