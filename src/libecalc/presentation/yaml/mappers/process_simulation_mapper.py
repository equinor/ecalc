from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.stream_distribution.common_stream_distribution import HasCapacity
from libecalc.domain.process.stream_distribution.priorities_stream_distribution import HasValidity
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class CompressorTrainStreamDistributionItem(HasCapacity, HasValidity):
    """Connects a compressor train's solver to the stream distribution system."""

    def __init__(
        self,
        solver: OutletPressureSolver,
        pressure_constraint: FloatConstraint,
        compressors: list[Compressor],
        runner: ProcessRunner,
    ):
        self._solver = solver
        self._pressure_constraint = pressure_constraint
        self._compressors = compressors
        self._runner = runner

    def is_valid(self, inlet_stream: FluidStream) -> bool:
        """Can the train operate at these inlet conditions?"""
        return self._solver.find_solution(
            pressure_constraint=self._pressure_constraint,
            inlet_stream=inlet_stream,
        ).success

    def get_unhandled_rate(self, inlet_stream: FluidStream) -> float:
        """How much rate (sm³/day) exceeds this train's capacity?"""
        max_rate = self.find_max_feasible_rate(
            inlet_stream=inlet_stream,
        )
        return max(0.0, inlet_stream.standard_rate_sm3_per_day - max_rate)

    def find_max_feasible_rate(
        self,
        inlet_stream: FluidStream,
    ) -> float:
        """
        Find the max standard rate this train can handle.

        If the solver can meet the pressure constraint, the full inlet rate is feasible.
        Otherwise, applies the solver's configuration (speed, anti-surge) and checks
        each compressor's stone wall to find the bottleneck.
        """
        solution = self._solver.find_solution(self._pressure_constraint, inlet_stream)
        if solution.success:
            # The train can handle the full rate — no need to search for a bottleneck.
            return inlet_stream.standard_rate_sm3_per_day

        # Apply the configuration from the (failed) solution to ensure
        # speed and anti-surge are set before querying compressor charts.
        self._runner.apply_configurations(solution.configuration)

        # Search for compressor with the lowest max rate
        min_max_rate = float("inf")
        for compressor in self._compressors:
            compressor_inlet = self._runner.run(
                inlet_stream=inlet_stream,
                to_id=compressor.get_id(),
            )
            max_rate = compressor.get_maximum_standard_rate(compressor_inlet)
            min_max_rate = min(min_max_rate, max_rate)

        return max(0.0, min_max_rate)
