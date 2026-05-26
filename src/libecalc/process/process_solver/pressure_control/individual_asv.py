from collections.abc import Sequence

from libecalc.common.numeric_methods import find_root
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.propagation_failure import PropagationFailure, TargetDirection
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import InfeasibleDuringSearch, Solution
from libecalc.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.process.process_units.compressor import Compressor


class IndividualASVPressureControlStrategy(PressureControlStrategy):
    """Varies recirculation rate independently per stage to meet equal pressure ratio.

    Each stage has its own recirculation loop and compressor. The total pressure ratio
    is distributed equally across stages using the geometric mean. Each stage is solved
    sequentially: the boundary is computed from the stage's actual inlet stream (which
    is only known after the previous stage has been solved).
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        compressors: Sequence[Compressor],
        root_finding_strategy: RootFindingStrategy,
    ):
        self._simulator = simulator
        self._recirculation_loop_ids = recirculation_loop_ids
        self._compressors = compressors
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        minimum_achievable_pressure_configurations = _minimum_achievable_pressure(
            simulator=self._simulator,
            recirculation_loop_ids=self._recirculation_loop_ids,
            compressors=self._compressors,
            inlet_stream=inlet_stream,
        )
        if isinstance(minimum_achievable_pressure_configurations, PropagationFailure):
            return Solution.failed(
                configuration=[],
                failure=minimum_achievable_pressure_configurations,
            )
        self._simulator.apply_configurations(minimum_achievable_pressure_configurations)
        minimum_outlet = self._simulator.run(inlet_stream=inlet_stream)
        if isinstance(minimum_outlet, PropagationFailure):
            return Solution.failed(
                configuration=minimum_achievable_pressure_configurations,
                failure=minimum_outlet,
            )
        if minimum_outlet.pressure_bara > target_pressure.value:
            # Even at maximum recirculation, the outlet pressure is still above the target.
            # The compressor train cannot deliver a pressure this low at the current speed.
            return Solution.target_pressure_unreachable(
                configuration=minimum_achievable_pressure_configurations,
                achievable_pressure_bara=minimum_outlet.pressure_bara,
                target_pressure_bara=target_pressure.value,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        n_stages = len(self._recirculation_loop_ids)
        pressure_ratio_per_stage = (target_pressure.value / inlet_stream.pressure_bara) ** (1.0 / n_stages)

        configurations: list[Configuration[RecirculationConfiguration | ChokeConfiguration]] = []

        for i, (recirculation_loop_id, compressor) in enumerate(zip(self._recirculation_loop_ids, self._compressors)):
            # Target pressure for this stage: cumulative from original inlet
            stage_target_pressure = inlet_stream.pressure_bara * (pressure_ratio_per_stage ** (i + 1))

            self._simulator.apply_configuration(
                Configuration(
                    configuration_handler_id=recirculation_loop_id,
                    value=RecirculationConfiguration(recirculation_rate=0.0),
                )
            )
            current_stream = self._simulator.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
            if isinstance(current_stream, PropagationFailure):
                return Solution.failed(configuration=configurations, failure=current_stream)
            boundary = compressor.get_recirculation_range(inlet_stream=current_stream)

            # Defaults bind the loop variables at def-time so each iteration's
            # closure refers to its own (recirculation_loop_id, compressor)
            # rather than the loop's last values.
            def recirculation_func(
                config: RecirculationConfiguration,
                _recirc_id: ConfigurationHandlerId = recirculation_loop_id,
                _compressor: Compressor = compressor,
            ) -> FluidStream | PropagationFailure:
                self._simulator.apply_configuration(Configuration(configuration_handler_id=_recirc_id, value=config))
                compressor_inlet = self._simulator.run(inlet_stream=inlet_stream, to_id=_compressor.get_id())
                if isinstance(compressor_inlet, PropagationFailure):
                    return compressor_inlet
                return _compressor.propagate_stream(inlet_stream=compressor_inlet)

            solver = RecirculationSolver(
                search_strategy=BinarySearchStrategy(tolerance=10e-3),
                root_finding_strategy=self._root_finding_strategy,
                recirculation_rate_boundary=boundary,
                target_pressure=FloatConstraint(stage_target_pressure),
            )

            solution = solver.solve(recirculation_func)
            configuration: Configuration[RecirculationConfiguration | ChokeConfiguration] = Configuration(
                configuration_handler_id=recirculation_loop_id, value=solution.configuration
            )
            configurations.append(configuration)

            if not solution.success:
                return Solution(
                    success=False,
                    configuration=configurations,
                    failure=solution.failure,
                )

        return Solution(
            success=True,
            configuration=configurations,
        )


class IndividualASVRateControlStrategy(PressureControlStrategy):
    """
    Finds a single ASV fraction applied proportionally across all stages.

    Each stage's available capacity is computed from its actual inlet stream,
    ensuring correct boundary calculation as the stream propagates through the train.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        compressors: Sequence[Compressor],
    ):
        self._simulator = simulator
        self._recirculation_loop_ids = recirculation_loop_ids
        self._compressors = compressors

    def _get_configurations_from_fraction(
        self,
        inlet_stream: FluidStream,
        asv_rate_fraction: float,
    ) -> Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]] | PropagationFailure:
        """Propagate stream through all stages, interpolating recirculation between min and max per stage.

        Returns the per-stage configurations, or a ``PropagationFailure`` if
        any intermediate run cannot reach a compressor inlet.
        """
        configurations: list[Configuration[RecirculationConfiguration | ChokeConfiguration]] = []
        for recirculation_loop_id, compressor in zip(self._recirculation_loop_ids, self._compressors):
            self._simulator.apply_configuration(
                Configuration(
                    configuration_handler_id=recirculation_loop_id,
                    value=RecirculationConfiguration(recirculation_rate=0.0),
                )
            )
            current_stream = self._simulator.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
            if isinstance(current_stream, PropagationFailure):
                return current_stream
            boundary = compressor.get_recirculation_range(inlet_stream=current_stream)
            recirculation_rate = boundary.min + asv_rate_fraction * (boundary.max - boundary.min)
            configurations.append(
                Configuration(
                    configuration_handler_id=recirculation_loop_id,
                    value=RecirculationConfiguration(
                        recirculation_rate=recirculation_rate,
                    ),
                )
            )
        return configurations

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        minimum_achievable_pressure_configurations = _minimum_achievable_pressure(
            simulator=self._simulator,
            recirculation_loop_ids=self._recirculation_loop_ids,
            compressors=self._compressors,
            inlet_stream=inlet_stream,
        )
        if isinstance(minimum_achievable_pressure_configurations, PropagationFailure):
            return Solution.failed(
                configuration=[],
                failure=minimum_achievable_pressure_configurations,
            )
        self._simulator.apply_configurations(minimum_achievable_pressure_configurations)
        minimum_outlet = self._simulator.run(inlet_stream=inlet_stream)
        if isinstance(minimum_outlet, PropagationFailure):
            return Solution.failed(
                configuration=minimum_achievable_pressure_configurations,
                failure=minimum_outlet,
            )
        if minimum_outlet.pressure_bara > target_pressure.value:
            # Even at maximum recirculation, the outlet pressure is still above the target.
            # The compressor train cannot deliver a pressure this low at the current speed.
            return Solution.target_pressure_unreachable(
                configuration=minimum_achievable_pressure_configurations,
                achievable_pressure_bara=minimum_outlet.pressure_bara,
                target_pressure_bara=target_pressure.value,
                direction=TargetDirection.MIN_ABOVE_TARGET,
            )

        def get_outlet_pressure(rate_fraction: float) -> float:
            test_configurations = self._get_configurations_from_fraction(
                inlet_stream=inlet_stream,
                asv_rate_fraction=rate_fraction,
            )
            if isinstance(test_configurations, PropagationFailure):
                raise InfeasibleDuringSearch(test_configurations)
            self._simulator.apply_configurations(test_configurations)
            out = self._simulator.run(inlet_stream=inlet_stream)
            if isinstance(out, PropagationFailure):
                raise InfeasibleDuringSearch(out)
            return out.pressure_bara

        # find_root searches for the recirculation fraction [0, 1] where
        # outlet_pressure(fraction) == target_pressure.
        # find_root raises if no solution exists within [0, 1].
        try:
            result_fraction = find_root(
                lower_bound=0.0,
                upper_bound=1.0,
                func=lambda x: get_outlet_pressure(x) - target_pressure.value,
            )
        except InfeasibleDuringSearch as exc:
            return Solution.failed(
                configuration=minimum_achievable_pressure_configurations,
                failure=exc.failure,
            )
        # Re-propagate with converged fraction so loops store correct rates
        configurations = self._get_configurations_from_fraction(
            inlet_stream=inlet_stream,
            asv_rate_fraction=result_fraction,
        )
        if isinstance(configurations, PropagationFailure):
            return Solution.failed(
                configuration=minimum_achievable_pressure_configurations,
                failure=configurations,
            )
        return Solution(
            success=True,
            configuration=configurations,
        )


def _minimum_achievable_pressure(
    simulator: ProcessRunner,
    recirculation_loop_ids: Sequence[ConfigurationHandlerId],
    compressors: Sequence[Compressor],
    inlet_stream: FluidStream,
) -> Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]] | PropagationFailure:
    """Propagate with maximum recirculation on every stage to find the lowest achievable pressure.

    Returns the per-stage configurations, or a ``PropagationFailure`` if any
    intermediate run cannot reach a compressor inlet.
    """
    configurations: list[Configuration[RecirculationConfiguration | ChokeConfiguration]] = []
    for loop, compressor in zip(recirculation_loop_ids, compressors):
        simulator.apply_configuration(
            Configuration(
                configuration_handler_id=loop,
                value=RecirculationConfiguration(recirculation_rate=0.0),
            )
        )
        current_stream = simulator.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
        if isinstance(current_stream, PropagationFailure):
            return current_stream
        boundary = compressor.get_recirculation_range(current_stream)
        configuration: Configuration[RecirculationConfiguration | ChokeConfiguration] = Configuration(
            configuration_handler_id=loop, value=RecirculationConfiguration(recirculation_rate=boundary.max)
        )
        simulator.apply_configuration(configuration)
        configurations.append(configuration)

    return configurations
