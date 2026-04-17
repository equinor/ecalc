import abc

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver_ratio import OutletPressureSolverRatio
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.process_system_solver import ProcessSystemSolver
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class FeasibilitySolver(abc.ABC):
    """Calculates how much of a given inlet rate exceeds what a compressor train
    can handle for a target pressure.
    """

    @abc.abstractmethod
    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        """Rate [sm³/day] that exceeds what this train can handle.

        This is the amount that must be redirected (e.g. via overflow)
        to another train in the stream distribution.
        """
        ...


class RunnerBasedFeasibility(FeasibilitySolver):
    """Uses runner + stonewall limits to find the maximum feasible rate.

    When the solver fails to meet the target pressure, applies the partial
    solution and queries each compressor's stonewall limit to determine the
    bottleneck rate.
    """

    def __init__(
        self,
        solver: ProcessSystemSolver,
        compressors: list[Compressor],
        runner: ProcessRunner,
    ):
        self._solver = solver
        self._compressors = compressors
        self._runner = runner

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        solution = self._solver.find_solution(target_pressure, inlet_stream)

        if solution.success:
            return 0.0

        self._runner.apply_configurations(solution.configuration)

        min_max_rate = float("inf")
        for compressor in self._compressors:
            compressor_inlet = self._runner.run(
                inlet_stream=inlet_stream,
                to_id=compressor.get_id(),
            )
            max_rate = compressor.get_maximum_standard_rate(compressor_inlet)
            min_max_rate = min(min_max_rate, max_rate)

        feasible_rate = max(0.0, min_max_rate)
        return max(0.0, inlet_stream.standard_rate_sm3_per_day - feasible_rate)


class RatioBasedFeasibility(FeasibilitySolver):
    """Computes excess rate from stonewall limits at each stage.

    Uses OutletPressureSolverRatio.get_max_standard_rate() to find the
    bottleneck stage's stonewall limit, then returns the excess above that.
    No runner needed — chart data lives on PressureRatioCompressor.
    """

    def __init__(self, solver: OutletPressureSolverRatio):
        self._solver = solver

    def get_excess_rate(
        self,
        inlet_stream: FluidStream,
        target_pressure: FloatConstraint,
    ) -> float:
        solution = self._solver.find_solution(target_pressure, inlet_stream)
        if solution.success:
            return 0.0

        max_rate = self._solver.get_max_standard_rate(target_pressure, inlet_stream)
        return max(0.0, inlet_stream.standard_rate_sm3_per_day - max_rate)
