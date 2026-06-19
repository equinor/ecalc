from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooLowError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import (
    Configuration,
    SpeedConfiguration,
    merge_configurations,
)
from libecalc.process.process_solver.finder import Finding
from libecalc.process.process_solver.finders.shaft_speed_finder import ShaftSpeedFinder
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.search_strategies import Bisect
from libecalc.process.process_solver.solver import (
    EosFailure,
    RateTooHighFailure,
    RateTooLowFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)


class PipelineSectionSolver:
    """Solves a single PipelineSection for a target outlet pressure by finding
    the compressor speed, anti-surge recirculation, and pressure-control
    settings required to meet it.
    """

    def __init__(self, pipeline_section: PipelineSection) -> None:
        self._pipeline_section = pipeline_section

    def _get_initial_speed_boundary(self) -> Boundary:
        return self._pipeline_section.speed_boundary

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Finding[SpeedConfiguration]:
        # The speed search evaluates the train with pressure control disengaged
        self._pipeline_section.pressure_control_strategy.reset()
        shaft_speed_finder = ShaftSpeedFinder(
            search_strategy=Bisect(),
            root_finding_strategy=self._pipeline_section.root_finding_strategy,
            boundary=self._get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            self._pipeline_section.anti_surge_strategy.reset()
            self._pipeline_section.runner.apply_configuration(
                Configuration(configuration_handler_id=self._pipeline_section.shaft_id, value=configuration),
            )
            try:
                return self._pipeline_section.runner.run(inlet_stream=inlet_stream)
            except RateTooLowError:
                solution = self._pipeline_section.anti_surge_strategy.apply(inlet_stream=inlet_stream)
                self._pipeline_section.runner.apply_configurations(solution.configuration)
                return self._pipeline_section.runner.run(inlet_stream=inlet_stream)

        return shaft_speed_finder.find(speed_func)

    def _get_outlet_stream(self, inlet_stream: FluidStream, configurations: Sequence[Configuration]):
        self._pipeline_section.runner.apply_configurations(configurations)
        return self._pipeline_section.runner.run(inlet_stream=inlet_stream)

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        speed_finding = self._find_speed_solution(pressure_constraint=pressure_constraint, inlet_stream=inlet_stream)

        shaft_config = Configuration(
            configuration_handler_id=self._pipeline_section.shaft_id,
            value=speed_finding.configuration,
        )

        if isinstance(speed_finding.failure, (RateTooHighFailure, RateTooLowFailure, EosFailure)):
            return Solution(configuration=[shaft_config], failure=speed_finding.failure)

        self._pipeline_section.runner.apply_configuration(shaft_config)
        anti_surge_solution = self._pipeline_section.anti_surge_strategy.apply(inlet_stream=inlet_stream)

        speed_and_anti_surge_configurations = [shaft_config, *anti_surge_solution.configuration]

        if not anti_surge_solution.success:
            return Solution(
                configuration=speed_and_anti_surge_configurations,
                failure=anti_surge_solution.failure,
            )

        if isinstance(speed_finding.failure, TargetPressureUnreachableFailure) and (
            speed_finding.failure.direction == TargetDirection.MAX_BELOW_TARGET
        ):
            failure = speed_finding.failure.with_source_id(self._pipeline_section.process_pipeline_id)
            return Solution(configuration=speed_and_anti_surge_configurations, failure=failure)

        outlet_at_chosen_speed = self._get_outlet_stream(
            inlet_stream=inlet_stream,
            configurations=speed_and_anti_surge_configurations,
        )

        if outlet_at_chosen_speed.pressure_bara == pressure_constraint:
            return Solution(configuration=speed_and_anti_surge_configurations)  # No pressure control needed

        pressure_control_solution = self._pipeline_section.pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )
        failure = pressure_control_solution.failure
        if isinstance(failure, TargetPressureUnreachableFailure) and failure.source_id is None:
            failure = failure.with_source_id(self._pipeline_section.process_pipeline_id)
        return Solution(
            configuration=merge_configurations(
                speed_and_anti_surge_configurations, pressure_control_solution.configuration
            ),
            failure=failure,
        )
