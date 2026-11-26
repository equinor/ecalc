from collections.abc import Sequence

from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump_solver.pump_pipeline_solver import PumpPipelineSolver
from libecalc.process.pump.pump_solver.pump_problem_solver import PumpProblemSolution
from libecalc.process.pump.stream_distribution.liquid_priorities_stream_distribution import HasLiquidValidity


class PumpStreamDistributionItem(HasLiquidValidity):
    """Connects the solver of one pump pipeline to the liquid stream distribution.

    ``is_valid`` solves the pipeline, so it leaves the pipeline's runner configured for the stream it
    was asked about. ``find_solutions`` for the selected stream configures the runner for that stream.
    """

    def __init__(self, pipeline_solver: PumpPipelineSolver, requested_outlet_pressures_bara: Sequence[float]):
        self._pipeline_solver = pipeline_solver
        self._requested_outlet_pressures_bara = tuple(requested_outlet_pressures_bara)

    def find_solutions(self, inlet_stream: LiquidStream) -> list[PumpProblemSolution]:
        return self._pipeline_solver.find_solutions(
            inlet_stream=inlet_stream,
            requested_outlet_pressures_bara=self._requested_outlet_pressures_bara,
        )

    def is_valid(self, inlet_stream: LiquidStream) -> bool:
        return all(solution.is_valid for solution in self.find_solutions(inlet_stream))
