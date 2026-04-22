from collections.abc import Sequence
from typing import Final

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.domain.process.process_solver.solver import (
    Solution,
    SolverFailureStatus,
    TargetNotAchievableEvent,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class MultiPressureSolver:
    """Tries to find the shaft speed satisfying N ordered pressure targets, one per segment. Segments share a
    single physical shaft. Each segment's runner covers a disjoint sub-sequence of the stream propagation chain.

    Independent OutletPressureSolver per segment (sequential) against its own pressure target. This gives the
    speed each segment would require if unconstrained. The segment requiring the highest speed is the binding
    constraint. At binding speed, non-binding segments produce more pressure than needed and must have it reduced
    by their pressure-control strategy.

    All segments are re-run in sequence at binding_speed. Anti-surge is applied first. If a segment's outlet
    still exceeds its target, the pressure-control strategy reduces it. The outlet of each segment feeds the inlet
    of the next. For all but one segment, speed changed from the individual evaluations. Therefore, recirculation
    is re-evaluated from scratch.
    """

    def __init__(
        self,
        segments: list[OutletPressureSolver],
    ) -> None:
        if len(segments) < 2:
            raise DomainValidationException("MultiPressureSolver requires at least 2 segments.")
        shaft_ids = {segment.shaft_id for segment in segments}
        if len(shaft_ids) != 1:
            raise DomainValidationException("All segments must share the same shaft_id.")
        self._shaft_id: Final = next(iter(shaft_ids))
        self._validate_pressure_control_placement(segments)
        self._segments: Final = segments

    @staticmethod
    def _validate_pressure_control_placement(segments: list[OutletPressureSolver]) -> None:
        """Upstream choke is only valid on the first segment; downstream choke only on the last."""
        for i, segment in enumerate(segments):
            strategy = segment.pressure_control_strategy
            is_first = i == 0
            is_last = i == len(segments) - 1
            if isinstance(strategy, UpstreamChokePressureControlStrategy) and not is_first:
                raise DomainValidationException(
                    f"UpstreamChokePressureControlStrategy is only valid for the first segment "
                    f"(segment {i} of {len(segments)})."
                )
            if isinstance(strategy, DownstreamChokePressureControlStrategy) and not is_last:
                raise DomainValidationException(
                    f"DownstreamChokePressureControlStrategy is only valid for the last segment "
                    f"(segment {i} of {len(segments)})."
                )

    def find_solution(
        self,
        pressure_targets: list[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        if len(pressure_targets) != len(self._segments):
            raise DomainValidationException(
                f"Number of pressure targets ({len(pressure_targets)}) must match "
                f"number of segments ({len(self._segments)})."
            )

        speed_configurations: list[SpeedConfiguration] = []
        current_inlet = inlet_stream
        for segment, target in zip(self._segments, pressure_targets):
            solution_for_segment = segment.find_solution(pressure_constraint=target, inlet_stream=current_inlet)
            speed_configuration = solution_for_segment.get_configuration(self._shaft_id)
            assert isinstance(speed_configuration, SpeedConfiguration)
            speed_configurations.append(speed_configuration)
            segment.runner.apply_configurations(solution_for_segment.configuration)
            current_inlet = segment.runner.run(inlet_stream=current_inlet)

        shaft_config = Configuration(
            configuration_handler_id=self._shaft_id,
            value=max(speed_configurations),
        )
        solution: Solution[Sequence[Configuration[OperatingConfiguration]]] = Solution(
            success=True, configuration=[shaft_config]
        )

        current_inlet = inlet_stream

        for segment, target in zip(self._segments, pressure_targets):
            segment.runner.apply_configuration(shaft_config)

            segment.anti_surge_strategy.reset()
            anti_surge_solution = segment.anti_surge_strategy.apply(inlet_stream=current_inlet)
            segment.runner.apply_configurations(anti_surge_solution.configuration)
            solution = solution.combine(anti_surge_solution)

            outlet = segment.runner.run(inlet_stream=current_inlet)

            if outlet.pressure_bara > target:
                pressure_control_solution = segment.pressure_control_strategy.apply(
                    target_pressure=target,
                    inlet_stream=current_inlet,
                )
                solution = solution.combine(pressure_control_solution)
                segment.runner.apply_configurations(pressure_control_solution.configuration)
                outlet = segment.runner.run(inlet_stream=current_inlet)
            elif outlet.pressure_bara < target:
                solution = Solution(
                    success=False,
                    configuration=solution.configuration,
                    failure_event=TargetNotAchievableEvent(
                        status=SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET,
                        achievable_value=outlet.pressure_bara,
                        target_value=target.value,
                        source_id=segment.process_pipeline_id,
                    ),
                )

            current_inlet = outlet

        return solution
