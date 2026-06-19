import logging
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooLowError
from libecalc.process.process_solver import solver_debug
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import (
    Configuration,
    RecirculationConfiguration,
    SpeedConfiguration,
    merge_configurations,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.process.process_units.compressor import Compressor as CompressorUnit

logger = logging.getLogger(__name__)


class PipelineSectionSolver:
    """Solves a single PipelineSection for a target outlet pressure by finding
    the compressor speed, anti-surge recirculation, and pressure-control
    settings required to meet it.
    """

    def __init__(self, pipeline_section: PipelineSection) -> None:
        self._pipeline_section = pipeline_section
        self._anti_surge_solution: Solution[Sequence[Configuration[RecirculationConfiguration]]] | None = None

    def _get_initial_speed_boundary(self) -> Boundary:
        return self._pipeline_section.speed_boundary

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[SpeedConfiguration]:
        # The speed search evaluates the train with pressure control disengaged
        self._pipeline_section.pressure_control_strategy.reset()
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
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

        speed_solution = speed_solver.solve(speed_func)

        return speed_solution

    def _get_outlet_stream(self, inlet_stream: FluidStream, configurations: Sequence[Configuration]):
        self._pipeline_section.runner.apply_configurations(configurations)
        return self._pipeline_section.runner.run(inlet_stream=inlet_stream)

    def get_anti_surge_solution(self) -> Solution[Sequence[Configuration[RecirculationConfiguration]]] | None:
        return self._anti_surge_solution

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        solver_debug.emit(
            "solve.start",
            target_pressure=pressure_constraint.value,
            inlet_rate=inlet_stream.standard_rate_sm3_per_day,
            speed_min=self._pipeline_section.speed_boundary.min,
            speed_max=self._pipeline_section.speed_boundary.max,
            pipeline_id=str(self._pipeline_section.process_pipeline_id),
            units=[
                {"id": str(u.get_id()), "type": u.__class__.__name__}
                | (
                    {
                        "chart": {
                            "curves": [
                                {
                                    "speed": curve.speed,
                                    "rates": list(curve.rate),
                                    "heads": [h / 1000.0 for h in curve.head],
                                }
                                for curve in u.compressor_chart.curves
                            ]
                        }
                    }
                    if isinstance(u, CompressorUnit)
                    else {}
                )
                for k, u in (
                    self._pipeline_section.runner._units.items()
                    if isinstance(self._pipeline_section.runner, ProcessPipelineRunner)
                    else []
                )
            ],
        )
        solver_debug.set_phase("speed_search")

        speed_solution = self._find_speed_solution(pressure_constraint=pressure_constraint, inlet_stream=inlet_stream)
        shaft_config = Configuration(
            configuration_handler_id=self._pipeline_section.shaft_id,
            value=speed_solution.configuration,
        )

        if isinstance(speed_solution.failure, RateTooHighFailure):
            solver_debug.emit(
                "solve.end", success=False, failure_type="RateTooHighFailure", speed=None, outlet_pressure=None
            )
            return Solution(
                success=False,
                configuration=[shaft_config],
                failure=speed_solution.failure,
            )

        solver_debug.set_phase(
            "anti_surge", reason="speed_found" if speed_solution.success else "max_speed_below_target"
        )
        self._pipeline_section.runner.apply_configuration(shaft_config)
        self._anti_surge_solution = self._pipeline_section.anti_surge_strategy.apply(inlet_stream=inlet_stream)

        speed_and_anti_surge_configurations = [shaft_config, *self._anti_surge_solution.configuration]

        if speed_solution.success:
            solver_debug.emit("solve.end", success=True, speed=speed_solution.configuration.speed, outlet_pressure=None)
            return Solution(success=True, configuration=speed_and_anti_surge_configurations)

        if not self._anti_surge_solution.success:
            solver_debug.emit(
                "solve.end",
                success=False,
                failure_type="AntiSurgeFailure",
                speed=speed_solution.configuration.speed,
                outlet_pressure=None,
            )
            return Solution(
                success=False,
                configuration=speed_and_anti_surge_configurations,
                failure=self._anti_surge_solution.failure,
            )

        outlet_at_chosen_speed = self._get_outlet_stream(
            inlet_stream=inlet_stream,
            configurations=speed_and_anti_surge_configurations,
        )

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            solver_debug.emit(
                "solve.end",
                success=False,
                failure_type="TargetPressureUnreachable",
                speed=speed_solution.configuration.speed,
                outlet_pressure=outlet_at_chosen_speed.pressure_bara,
            )
            return Solution.target_pressure_unreachable(
                configuration=speed_and_anti_surge_configurations,
                achievable_pressure_bara=outlet_at_chosen_speed.pressure_bara,
                target_pressure_bara=pressure_constraint.value,
                source_id=self._pipeline_section.process_pipeline_id,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        solver_debug.set_phase(
            "pressure_control",
            reason="outlet_pressure_above_target"
            if outlet_at_chosen_speed.pressure_bara > pressure_constraint.value
            else "anti_surge_complete",
        )
        pressure_control_solution = self._pipeline_section.pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )
        final_configs = merge_configurations(
            speed_and_anti_surge_configurations, pressure_control_solution.configuration
        )

        failure = pressure_control_solution.failure
        if isinstance(failure, TargetPressureUnreachableFailure) and failure.source_id is None:
            failure = failure.with_source_id(self._pipeline_section.process_pipeline_id)

        outlet_pressure = outlet_at_chosen_speed.pressure_bara
        solver_debug.emit(
            "solve.end",
            success=pressure_control_solution.success,
            speed=speed_solution.configuration.speed,
            outlet_pressure=outlet_pressure,
            failure_type=type(failure).__name__ if failure else None,
        )

        return Solution(
            success=pressure_control_solution.success,
            configuration=final_configs,
            failure=failure,
        )
