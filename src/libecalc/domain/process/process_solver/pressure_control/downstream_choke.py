from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import (
    ChokeConfiguration,
    DownstreamChokeSolver,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.stream_protocol import StreamWithPressure


class DownstreamChokePressureControlStrategy(PressureControlStrategy):
    """Meet target outlet pressure at fixed speed by applying downstream choking when needed.

    The choke is only applied when the baseline (unchoked) outlet pressure is above target.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        choke_configuration_handler_id: ConfigurationHandlerId,
    ):
        self._choke_configuration_handler_id = choke_configuration_handler_id
        self._simulator = simulator

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: StreamWithPressure,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        def outlet_with_choke(cfg: ChokeConfiguration) -> StreamWithPressure:
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=cfg)
            )
            return self._simulator.run(inlet_stream=inlet_stream)

        # 1) Baseline (no choking)
        baseline_config = ChokeConfiguration(delta_pressure=0.0)
        baseline_outlet_stream = outlet_with_choke(baseline_config)

        # If already at/below target, don't choke (can't increase pressure anyway).
        if baseline_outlet_stream.pressure_bara <= target_pressure:
            return Solution(
                success=baseline_outlet_stream.pressure_bara == target_pressure,
                configuration=[
                    Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=baseline_config)
                ],
            )

        # 2) Solve for needed downstream ΔP
        choke_solver = DownstreamChokeSolver(target_pressure=target_pressure.value)

        solution = choke_solver.solve(outlet_with_choke)
        return Solution(
            success=solution.success,
            configuration=[
                Configuration(
                    configuration_handler_id=self._choke_configuration_handler_id,
                    value=solution.configuration,
                )
            ],
        )
