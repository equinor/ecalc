"""Equal-ratio pressure solver for a train of independently-shafted compressors."""

from __future__ import annotations

from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_solver import MultiShaftSolver
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.solver import Solution


class MultiShaftEqualRatioSolver:
    """Wrapper around MultiShaftSolver that computes per-pipeline pressure targets
    using equal pressure ratio: target_i = P_in × ratio^(i+1).
    """

    def __init__(self, process_pipelines: Sequence[OutletPressureSolver]) -> None:
        self._process_pipelines = list(process_pipelines)
        self._solver = MultiShaftSolver(list(process_pipelines))

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        """Split overall pressure target into equal per-pipeline ratios and delegate."""
        n = len(self._process_pipelines)
        if n == 0:
            return Solution(success=True, configuration=[], failure_event=None)

        pressure_ratio = (pressure_constraint.value / inlet_stream.pressure_bara) ** (1.0 / n)

        # Rolling targets: each pipeline targets its actual inlet × ratio.
        # The final target is always the exact requested constraint.
        current_p = inlet_stream.pressure_bara
        targets: list[FloatConstraint] = []
        for _i in range(n):
            current_p *= pressure_ratio
            targets.append(FloatConstraint(current_p, abs_tol=pressure_constraint.abs_tol))
        targets[-1] = pressure_constraint

        return self._solver.find_solution(targets, inlet_stream)
