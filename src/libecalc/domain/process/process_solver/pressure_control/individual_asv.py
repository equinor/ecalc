from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.entities.process_units.gas_compressor import GasCompressor
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVPressureControlStrategy(PressureControlStrategy):
    """Varies recirculation rate independently per stage to meet equal pressure ratio.

    Each compressor stage has its own RecirculationLoop. The total pressure ratio is
    distributed equally across stages using the geometric mean. Stages are solved
    sequentially; the boundary is computed from the actual inlet to each loop, which
    is only known after all preceding units in the propagation_chain have been resolved.

    Non-RecirculationLoop units in the propagation_chain (conditioning, chokes, etc.)
    are propagated straight through without any recirculation control.
    """

    def __init__(
        self,
        propagation_chain: list[ProcessUnit | RecirculationLoop],
        recirculation_loops: list[RecirculationLoop],
        gas_compressors: list[GasCompressor],
        root_finding_strategy: RootFindingStrategy,
    ):
        self._propagation_chain = propagation_chain
        self._recirculation_loops = recirculation_loops
        self._gas_compressors = gas_compressors
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        if (
            _minimum_achievable_pressure(
                propagation_chain=self._propagation_chain,
                inlet_stream=inlet_stream,
            )
            > target_pressure.value
        ):
            return False

        n_stages = len(self._recirculation_loops)
        pressure_ratio_per_stage = (target_pressure.value / inlet_stream.pressure_bara) ** (1.0 / n_stages)

        current_stream = inlet_stream
        loop_index = 0
        for item in self._propagation_chain:
            if isinstance(item, RecirculationLoop):
                stage_target_pressure = inlet_stream.pressure_bara * (pressure_ratio_per_stage ** (loop_index + 1))
                boundary = item.get_recirculation_range(inlet_stream=current_stream)

                def recirculation_func(config, _loop=item, _stream=current_stream):
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

                item.set_recirculation_rate(solution.configuration.recirculation_rate)
                current_stream = item.propagate_stream(inlet_stream=current_stream)
                loop_index += 1
            else:
                current_stream = item.propagate_stream(inlet_stream=current_stream)

        return True


class IndividualASVRateControlStrategy(PressureControlStrategy):
    """Finds a single ASV fraction applied proportionally across all stages.

    Each stage's available recirculation capacity is computed from its actual inlet
    stream, ensuring correct boundary calculation as the stream propagates through
    the train. Non-RecirculationLoop units are propagated straight through.
    """

    def __init__(
        self,
        propagation_chain: list[ProcessUnit | RecirculationLoop],
        recirculation_loops: list[RecirculationLoop],
        gas_compressors: list[GasCompressor],
    ):
        self._propagation_chain = propagation_chain
        self._recirculation_loops = recirculation_loops
        self._gas_compressors = gas_compressors

    def _propagate_with_fraction(self, inlet_stream: FluidStream, asv_rate_fraction: float) -> FluidStream:
        """Propagate stream through all chain items, setting recirculation proportionally per loop."""
        current_stream = inlet_stream
        for item in self._propagation_chain:
            if isinstance(item, RecirculationLoop):
                boundary = item.get_recirculation_range(inlet_stream=current_stream)
                rate = boundary.min + asv_rate_fraction * (boundary.max - boundary.min)
                item.set_recirculation_rate(rate)
            current_stream = item.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        if (
            _minimum_achievable_pressure(
                propagation_chain=self._propagation_chain,
                inlet_stream=inlet_stream,
            )
            > target_pressure.value
        ):
            return False

        result_fraction = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: self._propagate_with_fraction(
                inlet_stream=inlet_stream,
                asv_rate_fraction=x,
            ).pressure_bara
            - target_pressure.value,
        )
        self._propagate_with_fraction(inlet_stream=inlet_stream, asv_rate_fraction=result_fraction)
        return True


def _minimum_achievable_pressure(
    propagation_chain: list[ProcessUnit | RecirculationLoop],
    inlet_stream: FluidStream,
) -> float:
    """Propagate with maximum recirculation on every loop to find the lowest achievable outlet pressure."""
    current_stream = inlet_stream
    for item in propagation_chain:
        if isinstance(item, RecirculationLoop):
            boundary = item.get_recirculation_range(current_stream)
            item.set_recirculation_rate(boundary.max)
        current_stream = item.propagate_stream(inlet_stream=current_stream)
    return current_stream.pressure_bara
