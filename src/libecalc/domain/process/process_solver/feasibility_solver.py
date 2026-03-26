from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class FeasibilitySolver:
    """
    Calculates how much of a given inlet rate exceeds what a compressor train
    can handle for a target pressure.

    Orchestrates OutletPressureSolver and queries compressor charts to find
    the feasible rate — the excess is redirected via stream distribution.
    """

    def __init__(
        self,
        outlet_pressure_solver: OutletPressureSolver,
        compressors: list[Compressor],
        runner: ProcessRunner,
    ):
        self._solver = outlet_pressure_solver
        self._compressors = compressors
        self._runner = runner

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        """
        Rate [sm³/day] that exceeds what this train can handle.

        This is the amount that must be redirected (e.g. via overflow)
        to another train in the stream distribution.
        """
        feasible = self._find_feasible_rate(inlet_stream, target_pressure)
        excess_rate = max(0.0, inlet_stream.standard_rate_sm3_per_day - feasible)
        return excess_rate

    def _find_feasible_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        """Highest standard rate [sm³/day] for which the train can meet target_pressure.

        Returns the full inlet rate if the solver succeeds, otherwise finds the
        bottleneck compressor's stone wall limit at the current operating point.
        """
        solution = self._solver.find_solution(target_pressure, inlet_stream)

        if solution.success:
            # The train can handle the full rate — no need to search for a bottleneck.
            return inlet_stream.standard_rate_sm3_per_day

        # Apply the configuration before querying compressor charts.
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

        feasible_rate = max(0.0, min_max_rate)

        return feasible_rate
