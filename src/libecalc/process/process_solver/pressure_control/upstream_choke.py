from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.process.process_solver.solver import Solution
from libecalc.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver

PRESSURE_CALCULATION_TOLERANCE = 1e-3


class UpstreamChokePressureControlStrategy(PressureControlStrategy):
    """
    Meet target outlet pressure at fixed speed by applying upstream choking when needed.

    The strategy models pressure control by reducing suction pressure (upstream choking).
    It computes a safe ΔP search interval from the inlet stream pressure at solve time,
    then uses a root-finding solver to find the ΔP that makes outlet pressure match the target.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        choke_configuration_handler_id: ConfigurationHandlerId,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._choke_configuration_handler_id = choke_configuration_handler_id
        self._simulator = simulator
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
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
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=config)
            )
            return self._simulator.run(
                inlet_stream=inlet_stream,
            )

        solution = solver.solve(choke_func)

        return Solution(
            success=solution.success,
            configuration=[
                Configuration(
                    configuration_handler_id=self._choke_configuration_handler_id, value=solution.configuration
                )
            ],
        )
