"""Sequential solver with caller-supplied pressure targets per pipeline section."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_section_solver import PipelineSectionSolver
from libecalc.process.process_solver.solver import Solution

logger = logging.getLogger(__name__)


class MultiShaftSolver:
    """Sequences independently-shafted process pipeline sections, each driven toward a
    caller-supplied pressure target. The outlet of one pipeline section feeds the inlet of the next.
    """

    def __init__(self, pipeline_sections: Sequence[PipelineSection]) -> None:
        self._pipeline_sections = list(pipeline_sections)

    def find_solution(
        self,
        pressure_targets: Sequence[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        """Run each pipeline section in flow order against its supplied pressure target."""
        assert len(pressure_targets) == len(self._pipeline_sections), (
            f"Number of pressure targets ({len(pressure_targets)}) must match "
            f"number of pipeline sections ({len(self._pipeline_sections)})."
        )

        if not self._pipeline_sections:
            return Solution(configuration=[], failure=None)

        current_inlet = inlet_stream
        all_configurations: list[Configuration[OperatingConfiguration]] = []
        failure = None

        for i, (pipeline_section, target) in enumerate(zip(self._pipeline_sections, pressure_targets)):
            solution = PipelineSectionSolver(pipeline_section).find_solution(target, current_inlet)
            all_configurations.extend(solution.configuration)

            if not solution.success:
                if failure is None:
                    failure = solution.failure
                logger.debug("PipelineSection %d failed to reach target %.1f bara.", i, target.value)

            pipeline_section.runner.apply_configurations(solution.configuration)
            current_inlet = pipeline_section.runner.run(current_inlet)

        return Solution(
            configuration=all_configurations,
            failure=failure,
        )
