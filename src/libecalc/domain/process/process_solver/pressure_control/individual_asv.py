from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.operating_envelope import OperatingEnvelope
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVPressureControlStrategy(PressureControlStrategy):
    """Varies recirculation rate independently per stage to meet equal pressure ratio.

    Each stage has its own recirculation loop and compressor. The total pressure ratio
    is distributed equally across stages using the geometric mean. Each stage is solved
    sequentially: the boundary is computed from the stage's actual inlet stream (which
    is only known after the previous stage has been solved).
    """

    def __init__(
        self,
        recirculation_loops: list[RecirculationLoop],
        compressors: list[CompressorStageProcessUnit],
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_loops = recirculation_loops
        self._compressors = compressors
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        if (
            OperatingEnvelope.minimum_achievable_pressure(
                recirculation_loops=self._recirculation_loops, compressors=self._compressors, inlet_stream=inlet_stream
            )
            > target_pressure.value
        ):
            # Even at maximum recirculation, the outlet pressure is still above the target.
            # The compressor train cannot deliver a pressure this low at the current speed.
            return False

        n_stages = len(self._recirculation_loops)
        pressure_ratio_per_stage = (target_pressure.value / inlet_stream.pressure_bara) ** (1.0 / n_stages)

        current_stream = inlet_stream
        for i, (recirculation_loop, compressor) in enumerate(zip(self._recirculation_loops, self._compressors)):
            # Target pressure for this stage: cumulative from original inlet
            stage_target_pressure = inlet_stream.pressure_bara * (pressure_ratio_per_stage ** (i + 1))

            # Boundary computed from actual inlet stream to this stage
            boundary = OperatingEnvelope.recirculation_rate_boundary(compressor=compressor, inlet_stream=current_stream)

            def recirculation_func(config, _loop=recirculation_loop, _stream=current_stream):
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
            recirculation_loop.set_recirculation_rate(solution.configuration.recirculation_rate)
            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)

        return True


class IndividualASVRateControlStrategy(PressureControlStrategy):
    """
    Finds a single ASV fraction applied proportionally across all stages.

    Each stage's available capacity is computed from its actual inlet stream,
    ensuring correct boundary calculation as the stream propagates through the train.
    """

    def __init__(
        self,
        recirculation_loops: list[RecirculationLoop],
        compressors: list[CompressorStageProcessUnit],
    ):
        self._recirculation_loops = recirculation_loops
        self._compressors = compressors

    def _propagate_with_fraction(self, inlet_stream: FluidStream, asv_rate_fraction: float) -> FluidStream:
        """Propagate stream through all stages with a given ASV fraction.

        For each stage, recirculation rate is set to the maximum of:
        - asv_rate_fraction * available_capacity
        - the stage's minimum recirculation rate (to stay within capacity)
        """
        current_stream = inlet_stream
        for recirculation_loop, compressor in zip(self._recirculation_loops, self._compressors):
            boundary = OperatingEnvelope.recirculation_rate_boundary(compressor=compressor, inlet_stream=current_stream)
            available_capacity = boundary.max - inlet_stream.standard_rate_sm3_per_day
            recirculation_rate = max(asv_rate_fraction * available_capacity, boundary.min)
            recirculation_loop.set_recirculation_rate(recirculation_rate)
            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        if (
            OperatingEnvelope.minimum_achievable_pressure(
                recirculation_loops=self._recirculation_loops, compressors=self._compressors, inlet_stream=inlet_stream
            )
            > target_pressure.value
        ):
            # Even at maximum recirculation, the outlet pressure is still above the target.
            # The compressor train cannot deliver a pressure this low at the current speed.
            return False

        # find_root searches for the recirculation fraction [0, 1] where
        # outlet_pressure(fraction) == target_pressure.
        # find_root raises if no solution exists within [0, 1].
        _ = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: self._propagate_with_fraction(
                inlet_stream=inlet_stream,
                asv_rate_fraction=x,
            ).pressure_bara
            - target_pressure.value,
        )
        return True
