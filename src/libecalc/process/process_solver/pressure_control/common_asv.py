from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import InfeasiblePressureError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import (
    InfeasiblePressureFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.process.process_units.compressor import Compressor


class CommonASVPressureControlStrategy(PressureControlStrategy):
    """Varies a single recirculation rate across the entire train to meet target pressure.

    The strategy owns the compressor reference needed to compute the recirculation
    boundary at solve time, since boundary depends on speed which may not be set
    at construction time.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        recirculation_loop_id: ConfigurationHandlerId,
        first_compressor: Compressor,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._simulator = simulator
        self._recirculation_loop_id = recirculation_loop_id
        self._first_compressor = first_compressor
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        def recirculation_func(config: RecirculationConfiguration) -> FluidStream:
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._recirculation_loop_id, value=config)
            )
            return self._simulator.run(inlet_stream=inlet_stream)

        # Reset recirculation before computing the boundary — the mixer may carry
        # residual state from anti-surge, which inflates the inlet rate and
        # shrinks the recirculation range.
        self._simulator.apply_configuration(
            Configuration(
                configuration_handler_id=self._recirculation_loop_id,
                value=RecirculationConfiguration(recirculation_rate=0.0),
            )
        )

        boundary_solution = self._compute_recirculation_boundary(inlet_stream)
        if not boundary_solution.success:
            return Solution(success=False, configuration=[], failure=boundary_solution.failure)
        boundary = boundary_solution.configuration

        min_configuration = RecirculationConfiguration(recirculation_rate=boundary.max)
        min_pressure_stream = recirculation_func(min_configuration)

        if min_pressure_stream.pressure_bara > target_pressure.value:
            return Solution(
                success=False,
                configuration=[
                    Configuration(
                        configuration_handler_id=self._recirculation_loop_id,
                        value=min_configuration,
                    )
                ],
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=min_pressure_stream.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MIN_ABOVE_TARGET,
                ),
            )

        solver = RecirculationSolver(
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )

        solution = solver.solve(recirculation_func)
        return Solution(
            success=solution.success,
            configuration=[
                Configuration(
                    configuration_handler_id=self._recirculation_loop_id,
                    value=solution.configuration,
                )
            ],
            failure=solution.failure,
        )

    def _compute_recirculation_boundary(self, inlet_stream: FluidStream) -> Solution[Boundary]:
        try:
            compressor_inlet_stream = self._simulator.run(
                inlet_stream=inlet_stream, to_id=self._first_compressor.get_id()
            )
        except InfeasiblePressureError as e:
            return Solution(
                success=False,
                configuration=Boundary(min=0, max=0),
                failure=InfeasiblePressureFailure.from_error(e),
            )
        boundary = self._first_compressor.get_recirculation_range(compressor_inlet_stream)
        return Solution(success=True, configuration=boundary)
