from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class FeasibilitySolver:
    """Computes the inlet rate excess a compressor train cannot handle at a target pressure."""

    def __init__(
        self,
        outlet_pressure_solver: OutletPressureSolver,
        runner: ProcessRunner,
    ):
        self._solver = outlet_pressure_solver
        self._runner = runner

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        """Rate [sm³/day] that exceeds what this train can handle."""
        solution = self._solver.find_solution(target_pressure, inlet_stream)
        if solution.success:
            return 0.0
        self._runner.apply_configurations(solution.configuration)
        max_rate = self._runner.get_max_standard_rate(inlet_stream)
        return max(0.0, inlet_stream.standard_rate_sm3_per_day - max_rate)
