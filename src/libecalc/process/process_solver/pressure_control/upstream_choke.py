from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
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

    When the demanded flow lies below the surge line, the anti-surge strategy is re-evaluated
    at every choke probe so that the compressor's recirculation rate is consistent with the
    actual (post-choke) suction pressure — rather than the pre-choke recirculation that
    would otherwise be frozen by the outer solver.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        choke_configuration_handler_id: ConfigurationHandlerId,
        root_finding_strategy: RootFindingStrategy,
        anti_surge_strategy: AntiSurgeStrategy,
    ):
        self._choke_configuration_handler_id = choke_configuration_handler_id
        self._simulator = simulator
        self._root_finding_strategy = root_finding_strategy
        self._anti_surge_strategy = anti_surge_strategy
        self._last_anti_surge_configurations: Sequence[Configuration[RecirculationConfiguration]] = []

    def reset(self) -> None:
        self._simulator.reset_configuration_handler(self._choke_configuration_handler_id)

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
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._choke_configuration_handler_id, value=config)
            )
            anti_surge_solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
            for anti_surge_configuration in anti_surge_solution.configuration:
                self._simulator.apply_configuration(anti_surge_configuration)
            self._last_anti_surge_configurations = anti_surge_solution.configuration
            return self._simulator.run(inlet_stream=inlet_stream)

        solution = solver.solve(choke_func)

        return Solution(
            success=solution.success,
            configuration=[
                *self._last_anti_surge_configurations,
                Configuration(
                    configuration_handler_id=self._choke_configuration_handler_id, value=solution.configuration
                ),
            ],
            failure=solution.failure,
        )
