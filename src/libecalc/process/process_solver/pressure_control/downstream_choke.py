from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.finders.choke_delta_pressure_finders import DownstreamChokeDeltaPressureFinder
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.solver import Solution, TargetDirection, TargetPressureUnreachableFailure


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

    def reset(self) -> None:
        self._simulator.reset_configuration_handler(self._choke_configuration_handler_id)

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        def outlet_with_choke(cfg: ChokeConfiguration) -> FluidStream:
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=cfg)
            )
            return self._simulator.run(inlet_stream=inlet_stream)

        # 1) Baseline (no choking)
        baseline_config = ChokeConfiguration(delta_pressure=0.0)
        baseline_outlet_stream = outlet_with_choke(baseline_config)

        # If already at/below target, don't choke (can't increase pressure anyway).
        if baseline_outlet_stream.pressure_bara <= target_pressure:
            choke_config = [
                Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=baseline_config)
            ]
            if baseline_outlet_stream.pressure_bara == target_pressure:
                return Solution(configuration=choke_config)
            return Solution(
                configuration=choke_config,
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=baseline_outlet_stream.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MAX_BELOW_TARGET,
                ),
            )

        # 2) Solve for needed downstream ΔP
        choke_finder = DownstreamChokeDeltaPressureFinder(target_pressure=target_pressure.value)

        finding = choke_finder.find(outlet_with_choke)
        return Solution(
            configuration=[
                Configuration(
                    configuration_handler_id=self._choke_configuration_handler_id,
                    value=finding.configuration,
                )
            ],
            failure=finding.failure,
        )
