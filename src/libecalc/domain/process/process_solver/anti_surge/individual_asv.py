from collections.abc import Sequence
from typing import override

from libecalc.domain.process.process_pipeline.process_error import RateTooHighError
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.solver import (
    OutsideCapacityEvent,
    Solution,
    SolverFailureStatus,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.unit_protocol import RecirculatingUnit
from libecalc.domain.process.value_objects.stream_protocol import StreamWithPressure


class IndividualASVAntiSurgeStrategy(AntiSurgeStrategy):
    """Anti-surge / minimum-flow strategy for INDIVIDUAL ASV topology.

    One recirculation loop per stage. Works for both compressor anti-surge and
    pump minimum-flow bypass — any unit satisfying RecirculatingUnit.
    """

    def __init__(
        self,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        units: Sequence[RecirculatingUnit],
        simulator: ProcessRunner,
    ):
        assert len(recirculation_loop_ids) == len(units)
        self._recirculation_loop_ids = recirculation_loop_ids
        self._units = units
        self._simulator = simulator

    def _apply_recirculation_configuration(self, loop_id: ConfigurationHandlerId, recirculation_rate: float):
        self._simulator.apply_configuration(
            Configuration(
                configuration_handler_id=loop_id,
                value=RecirculationConfiguration(
                    recirculation_rate=recirculation_rate,
                ),
            )
        )

    @override
    def reset(self) -> None:
        for loop_id in self._recirculation_loop_ids:
            self._simulator.apply_configuration(
                Configuration(
                    configuration_handler_id=loop_id,
                    value=RecirculationConfiguration(
                        recirculation_rate=0.0,
                    ),
                )
            )

    @override
    def apply(self, inlet_stream: StreamWithPressure) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        configurations: Sequence[Configuration[RecirculationConfiguration]] = []
        for loop_id, unit in zip(self._recirculation_loop_ids, self._units, strict=True):
            try:
                inlet_stream_unit = self._simulator.run(inlet_stream=inlet_stream, to_id=unit.get_id())
            except RateTooHighError as e:
                return Solution(
                    success=False,
                    configuration=configurations,
                    failure_event=OutsideCapacityEvent(
                        status=SolverFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
                        actual_value=e.actual_rate,
                        boundary_value=e.boundary_rate,
                        source_id=e.process_unit_id,
                    ),
                )
            max_actual_rate = unit.maximum_flow_rate
            if inlet_stream_unit.volumetric_rate_m3_per_hour > max_actual_rate:  # pyright: ignore[reportAttributeAccessIssue]
                return Solution(
                    success=False,
                    configuration=configurations,
                    failure_event=OutsideCapacityEvent(
                        status=SolverFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
                        actual_value=inlet_stream_unit.volumetric_rate_m3_per_hour,  # pyright: ignore[reportAttributeAccessIssue]
                        boundary_value=max_actual_rate,
                        source_id=unit.get_id(),
                    ),
                )
            boundary = unit.get_recirculation_range(inlet_stream=inlet_stream_unit)
            configuration: Configuration[RecirculationConfiguration] = Configuration(
                configuration_handler_id=loop_id,
                value=RecirculationConfiguration(
                    recirculation_rate=boundary.min,
                ),
            )
            configurations.append(configuration)
            self._simulator.apply_configuration(configuration)

        return Solution(
            success=True,
            configuration=configurations,
        )
