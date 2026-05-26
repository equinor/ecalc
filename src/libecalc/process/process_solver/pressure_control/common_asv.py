from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.propagation_failure import PropagationFailure, TargetDirection
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import Solution
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
        def recirculation_func(config: RecirculationConfiguration) -> FluidStream | PropagationFailure:
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._recirculation_loop_id, value=config)
            )
            return self._simulator.run(inlet_stream=inlet_stream)

        # Check feasibility: can we reach target pressure at maximum recirculation?
        # Reset recirculation before computing the boundary — the mixer may carry
        # residual state from anti-surge, which inflates the inlet rate and
        # shrinks the recirculation range.
        self._simulator.apply_configuration(
            Configuration(
                configuration_handler_id=self._recirculation_loop_id,
                value=RecirculationConfiguration(recirculation_rate=0.0),
            )
        )
        compressor_inlet = self._simulator.run(inlet_stream=inlet_stream, to_id=self._first_compressor.get_id())
        if isinstance(compressor_inlet, PropagationFailure):
            return Solution.failed(
                configuration=[
                    Configuration(
                        configuration_handler_id=self._recirculation_loop_id,
                        value=RecirculationConfiguration(recirculation_rate=0.0),
                    )
                ],
                failure=compressor_inlet,
            )
        boundary = self._first_compressor.get_recirculation_range(compressor_inlet)
        min_configuration = RecirculationConfiguration(recirculation_rate=boundary.max)
        min_pressure_result = recirculation_func(min_configuration)
        min_config_list = [Configuration(configuration_handler_id=self._recirculation_loop_id, value=min_configuration)]
        if isinstance(min_pressure_result, PropagationFailure):
            return Solution.failed(configuration=min_config_list, failure=min_pressure_result)

        if min_pressure_result.pressure_bara > target_pressure.value:
            return Solution.target_pressure_unreachable(
                configuration=min_config_list,
                achievable_pressure_bara=min_pressure_result.pressure_bara,
                target_pressure_bara=target_pressure.value,
                direction=TargetDirection.MIN_ABOVE_TARGET,
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
            failure=solution.failure,
            configuration=[
                Configuration(
                    configuration_handler_id=self._recirculation_loop_id,
                    value=solution.configuration,
                )
            ],
        )
