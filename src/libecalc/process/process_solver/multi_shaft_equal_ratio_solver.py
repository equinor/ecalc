"""Equal-ratio pressure solver for a train of independently-shafted compressors."""

from __future__ import annotations

from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_solver import MultiShaftSolver
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_solver import PipelineSolver
from libecalc.process.process_solver.solver import Solution


class MultiShaftEqualRatioSolver(PipelineSolver):
    """Wrapper around MultiShaftSolver that computes per-pipeline section pressure targets
    using equal pressure ratio: target_i = P_in × ratio^(i+1).
    """

    def __init__(self, pipeline_sections: Sequence[PipelineSection]) -> None:
        self._pipeline_sections = list(pipeline_sections)
        self._solver = MultiShaftSolver(list(pipeline_sections))

    def find_solution(
        self,
        pressure_targets: list[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:

        assert len(pressure_targets) == 1
        pressure_target: FloatConstraint = pressure_targets[0]

        """Split overall pressure target into equal per-pipeline section ratios and delegate."""
        n = len(self._pipeline_sections)
        if n == 0:
            return Solution(configuration=[], failure=None)

        pressure_ratio = (pressure_target.value / inlet_stream.pressure_bara) ** (1.0 / n)

        # Rolling targets: each pipeline section targets its actual inlet × ratio.
        # The final target is always the exact requested constraint.
        current_p = inlet_stream.pressure_bara
        targets: list[FloatConstraint] = []
        for _i in range(n):
            current_p *= pressure_ratio
            targets.append(FloatConstraint(current_p, abs_tol=pressure_target.abs_tol))
        targets[-1] = pressure_target

        return self._solver.find_solution(targets, inlet_stream)
