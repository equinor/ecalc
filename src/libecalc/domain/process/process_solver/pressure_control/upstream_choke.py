from dataclasses import dataclass

from libecalc.domain.process.compressor.core.train.utils.common import PRESSURE_CALCULATION_TOLERANCE
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class UpstreamChokeRunner:
    def __init__(self, process_system: ProcessSystem, upstream_choke: Choke):
        self._process_system = process_system
        self._upstream_choke = upstream_choke

    def run(self, inlet_stream: FluidStream, upstream_delta_pressure: float) -> FluidStream:
        self._upstream_choke.set_pressure_change(pressure_change=upstream_delta_pressure)
        return self._process_system.propagate_stream(inlet_stream=inlet_stream)


class UpstreamChokePressureControlStrategy(PressureControlStrategy):
    """
    Meet target outlet pressure at fixed speed by applying upstream choking when needed.

    The strategy models pressure control by reducing suction pressure (upstream choking).
    It computes a safe ΔP search interval from the inlet stream pressure at solve time,
    then uses a root-finding solver to find the ΔP that makes outlet pressure match the target.
    """

    def __init__(
        self,
        runner: "UpstreamChokeRunner",
        root_finding_strategy: RootFindingStrategy,
    ):
        self._runner = runner
        self._root_finding_strategy = root_finding_strategy

    def apply(self, target_pressure: FloatConstraint, inlet_stream: FluidStream) -> bool:
        # Use a small margin to avoid evaluating exactly at the physical/numerical extremes:
        # ΔP = 0 (no choke) and ΔP = inlet_pressure (zero/negative suction pressure).
        delta_pressure_boundary = Boundary(
            min=PRESSURE_CALCULATION_TOLERANCE,
            max=inlet_stream.pressure_bara - PRESSURE_CALCULATION_TOLERANCE,
        )

        solver = UpstreamChokeSolver(
            root_finding_strategy=self._root_finding_strategy,
            target_pressure=target_pressure.value,
            delta_pressure_boundary=delta_pressure_boundary,
        )

        def choke_func(config: ChokeConfiguration) -> FluidStream:
            # The runner is responsible for interpreting upstream ΔP as reduced suction pressure
            # seen by the downstream process system.
            return self._runner.run(
                inlet_stream=inlet_stream,
                upstream_delta_pressure=config.delta_pressure,
            )

        solution = solver.solve(choke_func)

        # Re-run with the chosen configuration to leave the choke/process state configured.
        outlet_stream_after_choke = choke_func(solution.configuration)

        return outlet_stream_after_choke.pressure_bara == target_pressure
