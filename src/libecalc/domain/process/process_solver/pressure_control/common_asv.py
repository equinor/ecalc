from collections.abc import Sequence

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solver import (
    Solution,
    SolverFailureStatus,
    TargetNotAchievableEvent,
)
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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

        # Check feasibility: can we reach target pressure at maximum recirculation?
        boundary = self._first_compressor.get_recirculation_range(inlet_stream)
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
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET,
                    achievable_value=min_pressure_stream.pressure_bara,
                    target_value=target_pressure.value,
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
        )
