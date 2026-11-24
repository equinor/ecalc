from collections.abc import Sequence

from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump_solver.pump_problem_solver import PumpProblemSolution, PumpProblemSolver


class PumpPipelineSolver:
    """Solves the pump problems of one pump pipeline, in flow order.

    A problem solver reads the stream that the units upstream of its pump give with their current
    configuration, so every problem is solved on each call, from the first to the last.
    """

    def __init__(self, problem_solvers: Sequence[PumpProblemSolver]):
        self._problem_solvers = tuple(problem_solvers)

    def find_solutions(
        self, inlet_stream: LiquidStream, requested_outlet_pressures_bara: Sequence[float]
    ) -> list[PumpProblemSolution]:
        """One solution per pump problem, for the stream at the inlet of the pipeline."""
        return [
            problem_solver.find_solution(
                inlet_stream=inlet_stream,
                requested_outlet_pressure_bara=requested_outlet_pressure_bara,
            )
            for problem_solver, requested_outlet_pressure_bara in zip(
                self._problem_solvers, requested_outlet_pressures_bara, strict=True
            )
        ]
