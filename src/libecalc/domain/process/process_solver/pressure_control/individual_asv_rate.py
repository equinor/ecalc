from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import (
    BoundaryFactory,
    PressureControlStrategy,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVRateControlStrategy(PressureControlStrategy):
    """Finds a single ASV fraction applied proportionally across all stages.

    Each stage's available capacity is computed from its actual inlet stream,
    ensuring correct boundary calculation as the stream propagates through the train.
    """

    def __init__(
        self,
        recirculation_loops: list[RecirculationLoop],
        get_boundary_for_stage: BoundaryFactory,
    ):
        self._recirculation_loops = recirculation_loops
        self._get_boundary_for_stage = get_boundary_for_stage

    def _propagate_with_fraction(self, inlet_stream: FluidStream, asv_rate_fraction: float) -> FluidStream:
        """Propagate stream through all stages with a given ASV fraction.

        For each stage, recirculation rate is set to the maximum of:
        - asv_rate_fraction * available_capacity
        - the stage's minimum recirculation rate (to stay within capacity)
        """
        current_stream = inlet_stream
        for i, loop in enumerate(self._recirculation_loops):
            boundary = self._get_boundary_for_stage(i, current_stream)
            available_capacity = boundary.max - inlet_stream.standard_rate_sm3_per_day
            recirculation_rate = max(asv_rate_fraction * available_capacity, boundary.min)
            loop.set_recirculation_rate(recirculation_rate)
            current_stream = loop.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def apply(
        self,
        *,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
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
