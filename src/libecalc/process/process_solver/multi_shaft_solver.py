"""Sequential solver with caller-supplied pressure targets per pipeline section."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import ProcessError
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_section_solver import PipelineSectionSolver
from libecalc.process.process_solver.search_strategies import DidNotConvergeError
from libecalc.process.process_solver.solver import (
    ConvergenceFailure,
    Solution,
    process_error_to_failure,
)

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
        try:
            return self._find_solution(pressure_targets, inlet_stream)
        except DidNotConvergeError as e:
            return Solution(configuration=[], failure=ConvergenceFailure.from_error(e))
        except ProcessError as e:
            return Solution(configuration=[], failure=process_error_to_failure(e))

    def _find_solution(
        self,
        pressure_targets: Sequence[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        if not self._pipeline_sections:
            return Solution(configuration=[])

        current_inlet = inlet_stream
        all_configurations: list[Configuration[OperatingConfiguration]] = []

        for i, (pipeline_section, target) in enumerate(zip(self._pipeline_sections, pressure_targets, strict=True)):
            solution = PipelineSectionSolver(pipeline_section).find_solution(target, current_inlet)
            all_configurations.extend(solution.configuration)

            if not solution.success:
                logger.debug("PipelineSection %d failed to reach target %.1f bara.", i, target.value)
                return Solution(configuration=all_configurations, failure=solution.failure)

            pipeline_section.runner.apply_configurations(solution.configuration)
            current_inlet = pipeline_section.runner.run(current_inlet)

        return Solution(configuration=all_configurations)
