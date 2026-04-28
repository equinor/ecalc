from collections.abc import Sequence
from typing import override

from libecalc.domain.process.entities.process_units.compressor import Compressor
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
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVAntiSurgeStrategy(AntiSurgeStrategy):
    """Anti-surge strategy for INDIVIDUAL ASV topology (one recirculation loop per stage).

    Propagates stage-by-stage, setting each stage’s ASV recirculation to the minimum feasible
    value based on that stage’s actual inlet stream, and returns the final outlet stream.

    Contract:
      - Mutates each stage's RecirculationLoop by setting its recirculation rate.
      - Returns the outlet stream after all stages have been propagated with minimum feasible recirculation.
    """

    def __init__(
        self,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        compressors: Sequence[Compressor],
        simulator: ProcessRunner,
    ):
        assert len(recirculation_loop_ids) == len(compressors)
        self._recirculation_loop_ids = recirculation_loop_ids
        self._compressors = compressors
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
    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        configurations: Sequence[Configuration[RecirculationConfiguration]] = []
        for loop_id, compressor in zip(self._recirculation_loop_ids, self._compressors, strict=True):
            try:
                inlet_stream_compressor = self._simulator.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
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
            max_actual_rate = compressor.maximum_flow_rate
            if inlet_stream_compressor.volumetric_rate_m3_per_hour > max_actual_rate:
                return Solution(
                    success=False,
                    configuration=configurations,
                    failure_event=OutsideCapacityEvent(
                        status=SolverFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
                        actual_value=inlet_stream_compressor.volumetric_rate_m3_per_hour,
                        boundary_value=max_actual_rate,
                        source_id=compressor.get_id(),
                    ),
                )
            boundary = compressor.get_recirculation_range(inlet_stream=inlet_stream_compressor)
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
