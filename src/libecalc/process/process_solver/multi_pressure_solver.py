from collections.abc import Sequence
from typing import Final

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_section_solver import PipelineSectionSolver
from libecalc.process.process_solver.pressure_control.downstream_choke import DownstreamChokePressureControlStrategy
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_solver.solver import Solution, TargetDirection


class MultiPressureSolver:
    """Tries to find the shaft speed satisfying N ordered pressure targets, one per pipeline section. Pipeline sections share a
    single physical shaft. Each pipeline section's runner covers a disjoint sub-sequence of the stream propagation chain.

    Independent PipelineSectionSolver per pipeline section (sequential) against its own pressure target. This gives the
    speed each pipeline section would require if unconstrained. The pipeline section requiring the highest speed is the binding
    constraint. At binding speed, non-binding pipeline sections produce more pressure than needed and must have it reduced
    by their pressure-control strategy.

    All pipeline sections are re-run in sequence at binding_speed. Anti-surge is applied first. If a pipeline section's outlet
    still exceeds its target, the pressure-control strategy reduces it. The outlet of each pipeline section feeds the inlet
    of the next. For all but one pipeline section, speed changed from the individual evaluations. Therefore, recirculation
    is re-evaluated from scratch.
    """

    def __init__(
        self,
        pipeline_sections: list[PipelineSection],
    ) -> None:
        if len(pipeline_sections) < 2:
            raise EcalcValidationException("MultiPressureSolver requires at least 2 pipeline sections.")
        shaft_ids = {pipeline_section.shaft_id for pipeline_section in pipeline_sections}
        if len(shaft_ids) != 1:
            raise EcalcValidationException("All pipeline sections must share the same shaft_id.")
        self._shaft_id: Final = next(iter(shaft_ids))
        self._validate_pressure_control_placement(pipeline_sections)
        self._pipeline_sections: Final = pipeline_sections

    @staticmethod
    def _validate_pressure_control_placement(pipeline_sections: list[PipelineSection]) -> None:
        """Upstream choke is only valid on the first pipeline_section; downstream choke only on the last."""
        for i, pipeline_section in enumerate(pipeline_sections):
            strategy = pipeline_section.pressure_control_strategy
            is_first = i == 0
            is_last = i == len(pipeline_sections) - 1
            if isinstance(strategy, UpstreamChokePressureControlStrategy) and not is_first:
                raise EcalcValidationException(
                    f"UpstreamChokePressureControlStrategy is only valid for the first pipeline section "
                    f"(pipeline section {i} of {len(pipeline_sections)})."
                )
            if isinstance(strategy, DownstreamChokePressureControlStrategy) and not is_last:
                raise EcalcValidationException(
                    f"DownstreamChokePressureControlStrategy is only valid for the last pipeline section "
                    f"(pipeline section {i} of {len(pipeline_sections)})."
                )

    def find_solution(
        self,
        pressure_targets: list[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        if len(pressure_targets) != len(self._pipeline_sections):
            raise EcalcValidationException(
                f"Number of pressure targets ({len(pressure_targets)}) must match "
                f"number of pipeline sections ({len(self._pipeline_sections)})."
            )

        speed_configurations: list[SpeedConfiguration] = []
        current_inlet = inlet_stream
        for pipeline_section, target in zip(self._pipeline_sections, pressure_targets):
            solution_for_pipeline_section = PipelineSectionSolver(pipeline_section).find_solution(
                pressure_constraint=target, inlet_stream=current_inlet
            )
            if not solution_for_pipeline_section.success:
                return solution_for_pipeline_section
            speed_configuration = solution_for_pipeline_section.get_configuration(self._shaft_id)
            assert isinstance(speed_configuration, SpeedConfiguration)
            speed_configurations.append(speed_configuration)
            pipeline_section.runner.apply_configurations(solution_for_pipeline_section.configuration)
            current_inlet = pipeline_section.runner.run(inlet_stream=current_inlet)

        shaft_config = Configuration(
            configuration_handler_id=self._shaft_id,
            value=max(speed_configurations),
        )
        solution: Solution[Sequence[Configuration[OperatingConfiguration]]] = Solution(configuration=[shaft_config])

        current_inlet = inlet_stream

        for pipeline_section, target in zip(self._pipeline_sections, pressure_targets):
            pipeline_section.pressure_control_strategy.reset()  #  to clear a potential upstream/downstream choke
            pipeline_section.runner.apply_configuration(shaft_config)

            anti_surge_solution = pipeline_section.anti_surge_strategy.apply(inlet_stream=current_inlet)
            pipeline_section.runner.apply_configurations(anti_surge_solution.configuration)
            solution = solution.combine(anti_surge_solution)

            outlet = pipeline_section.runner.run(inlet_stream=current_inlet)

            if outlet.pressure_bara > target:
                pressure_control_solution = pipeline_section.pressure_control_strategy.apply(
                    target_pressure=target,
                    inlet_stream=current_inlet,
                )
                solution = solution.combine(pressure_control_solution)
                pipeline_section.runner.apply_configurations(pressure_control_solution.configuration)
                outlet = pipeline_section.runner.run(inlet_stream=current_inlet)
            elif outlet.pressure_bara < target:
                solution = Solution.target_pressure_unreachable(
                    configuration=solution.configuration,
                    achievable_pressure_bara=outlet.pressure_bara,
                    target_pressure_bara=target.value,
                    source_id=pipeline_section.process_pipeline_id,
                    direction=TargetDirection.MAX_BELOW_TARGET,
                )

            current_inlet = outlet

        return solution
