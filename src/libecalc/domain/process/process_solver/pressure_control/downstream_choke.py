from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import (
    ChokeConfiguration,
    DownstreamChokeSolver,
)
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class DownstreamChokeRunner:
    def __init__(self, process_system: ProcessSystem, downstream_choke: Choke):
        self._process_system = process_system
        self._downstream_choke = downstream_choke

    def run(self, inlet_stream: FluidStream, downstream_delta_pressure: float) -> FluidStream:
        self._downstream_choke.set_pressure_change(pressure_change=downstream_delta_pressure)
        return self._process_system.propagate_stream(inlet_stream=inlet_stream)


class DownstreamChokePressureControlStrategy(PressureControlStrategy):
    """Meet target outlet pressure at fixed speed by applying downstream choking when needed.

    The choke is only applied when the baseline (unchoked) outlet pressure is above target.
    """

    def __init__(
        self,
        runner: DownstreamChokeRunner,
    ):
        self._runner = runner

    def apply(self, target_pressure: FloatConstraint, inlet_stream: FluidStream) -> bool:
        # 1) Baseline (no choking)
        baseline_outlet_stream = self._runner.run(inlet_stream=inlet_stream, downstream_delta_pressure=0.0)

        # If already at/below target, don't choke (can't increase pressure anyway).
        if baseline_outlet_stream.pressure_bara <= target_pressure:
            return baseline_outlet_stream.pressure_bara == target_pressure

        # 2) Solve for needed downstream ΔP
        choke_solver = DownstreamChokeSolver(target_pressure=target_pressure.value)

        def outlet_with_choke(cfg: ChokeConfiguration) -> FluidStream:
            return self._runner.run(
                inlet_stream=inlet_stream,
                downstream_delta_pressure=cfg.delta_pressure,
            )

        solution = choke_solver.solve(outlet_with_choke)

        # Ensure final state matches the chosen configuration
        choked_outlet_stream = self._runner.run(
            inlet_stream=inlet_stream,
            downstream_delta_pressure=solution.configuration.delta_pressure,
        )

        return choked_outlet_stream.pressure_bara == target_pressure
