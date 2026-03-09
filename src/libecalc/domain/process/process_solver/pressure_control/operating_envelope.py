from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class OperatingEnvelope:
    """
    Defines operating limits for a compressor train.

    Responsible for calculating recirculation rate boundaries required to stay within compressor capacity limits.
    """

    @staticmethod
    def minimum_recirculation_rate(compressor: CompressorStageProcessUnit, inlet_stream: FluidStream) -> float:
        """
        Calculate the minimum recirculation rate for a given compressor and inlet stream to bring it inside capacity

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            float: The maximum recirculation rate.
        """
        min_rate = compressor.get_minimum_standard_rate(inlet_stream=inlet_stream) * (1 + EPSILON)
        return max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day)

    @staticmethod
    def maximum_recirculation_rate(compressor: CompressorStageProcessUnit, inlet_stream: FluidStream) -> float:
        """
        Calculate the maximum recirculation rate for a given compressor and inlet stream.

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            float: The maximum recirculation rate.
        """
        max_rate = compressor.get_maximum_standard_rate(inlet_stream=inlet_stream) * (1 - EPSILON)
        return max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day)

    @staticmethod
    def recirculation_rate_boundary(compressor: CompressorStageProcessUnit, inlet_stream: FluidStream) -> Boundary:
        """
        Get the recirculation rate boundary for a specific compressor.

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            Boundary: The recirculation rate boundary.
        """
        return Boundary(
            min=OperatingEnvelope.minimum_recirculation_rate(compressor=compressor, inlet_stream=inlet_stream),
            max=OperatingEnvelope.maximum_recirculation_rate(compressor=compressor, inlet_stream=inlet_stream),
        )

    @staticmethod
    def minimum_achievable_pressure(
        recirculation_loops: list[RecirculationLoop],
        compressors: list[CompressorStageProcessUnit],
        inlet_stream: FluidStream,
    ) -> float:
        """Propagate with maximum recirculation on every stage to find lowest achievable pressure."""
        current_stream = inlet_stream
        for loop, compressor in zip(recirculation_loops, compressors):
            boundary = OperatingEnvelope.recirculation_rate_boundary(compressor, current_stream)
            loop.set_recirculation_rate(boundary.max)
            current_stream = loop.propagate_stream(inlet_stream=current_stream)
        return current_stream.pressure_bara
