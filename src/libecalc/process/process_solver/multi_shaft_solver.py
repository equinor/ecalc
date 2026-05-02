"""Sequential solver with caller-supplied pressure targets per process pipeline."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.solver import Solution

logger = logging.getLogger(__name__)


class MultiShaftSolver:
    """Sequences independently-shafted process pipelines, each driven toward a
    caller-supplied pressure target.  The outlet of one pipeline feeds the
    inlet of the next.
    """

    def __init__(self, process_pipelines: Sequence[OutletPressureSolver]) -> None:
        self._process_pipelines = list(process_pipelines)

    def find_solution(
        self,
        pressure_targets: Sequence[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        """Run each process pipeline in flow order against its supplied pressure target."""
        assert len(pressure_targets) == len(self._process_pipelines), (
            f"Number of pressure targets ({len(pressure_targets)}) must match "
            f"number of process pipelines ({len(self._process_pipelines)})."
        )

        if not self._process_pipelines:
            return Solution(success=True, configuration=[], failure_event=None)

        current_inlet = inlet_stream
        all_configurations: list[Configuration[OperatingConfiguration]] = []
        failure_event = None
        overall_success = True

        for i, (pipeline, target) in enumerate(zip(self._process_pipelines, pressure_targets)):
            solution = pipeline.find_solution(target, current_inlet)
            all_configurations.extend(solution.configuration)

            if not solution.success:
                overall_success = False
                if failure_event is None:
                    failure_event = solution.failure_event
                logger.debug("Process pipeline %d failed to reach target %.1f bara.", i, target.value)

            pipeline.runner.apply_configurations(solution.configuration)
            current_inlet = pipeline.runner.run(current_inlet)

        return Solution(
            success=overall_success,
            configuration=all_configurations,
            failure_event=failure_event,
        )
