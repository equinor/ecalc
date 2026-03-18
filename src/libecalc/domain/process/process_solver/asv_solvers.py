from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.entities.shaft.shaft import ShaftId
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import Configuration, ProcessRunner
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import (
    ProcessSystemId,
)
from libecalc.domain.process.process_system.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ASVSolver:
    def __init__(
        self,
        shaft: Shaft,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        root_finding_strategy: RootFindingStrategy,
        speed_boundary: Boundary,
    ) -> None:
        self._shaft = shaft
        self._root_finding_strategy = root_finding_strategy
        self._anti_surge_strategy = anti_surge_strategy
        self._simulator = runner
        self._pressure_control_strategy = pressure_control_strategy
        self._speed_boundary = speed_boundary

        self._anti_surge_solution: Solution[list[Configuration[RecirculationConfiguration]]] | None = None

    def _get_initial_speed_boundary(self) -> Boundary:
        return self._speed_boundary

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[SpeedConfiguration]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self._get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            self._simulator.apply_configuration(
                Configuration(simulation_unit_id=self._shaft.get_id(), value=configuration)
            )
            self._anti_surge_strategy.reset()
            try:
                return self._simulator.run(inlet_stream=inlet_stream)
            except RateTooLowError:
                # Reset anti-surge control state before applying the strategy.
                solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
                self._simulator.apply_configurations(solution.configuration)
                return self._simulator.run(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)

        return speed_solution

    def _get_outlet_stream(self, inlet_stream: FluidStream, configurations: list[Configuration]):
        self._simulator.apply_configurations(configurations)
        return self._simulator.run(inlet_stream=inlet_stream)

    def get_anti_surge_solution(self) -> Solution[list[Configuration[RecirculationConfiguration]]]:
        assert self._anti_surge_solution is not None
        return self._anti_surge_solution

    def find_asv_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[list[Configuration]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        configurations: dict[ShaftId | ProcessUnitId | ProcessSystemId, Configuration] = {}
        speed_solution = self._find_speed_solution(pressure_constraint=pressure_constraint, inlet_stream=inlet_stream)
        configurations[self._shaft.get_id()] = Configuration(
            simulation_unit_id=self._shaft.get_id(),
            value=speed_solution.configuration,
        )

        self._simulator.apply_configurations(list(configurations.values()))
        self._anti_surge_strategy.reset()
        self._anti_surge_solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
        for anti_surge_configuration in self._anti_surge_solution.configuration:
            configurations[anti_surge_configuration.simulation_unit_id] = anti_surge_configuration

        if speed_solution.success:
            return Solution(
                success=True,
                configuration=list(configurations.values()),
            )

        outlet_at_chosen_speed = self._get_outlet_stream(
            inlet_stream=inlet_stream,
            configurations=list(configurations.values()),
        )

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            # Pressure control (ASV/choke) can only reduce outlet pressure. If we're already below target at chosen speed,
            # no pressure control can help.
            return Solution(
                success=False,
                configuration=list(configurations.values()),
            )

        pressure_control_solution = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )

        for pressure_control_configuration in pressure_control_solution.configuration:
            configurations[pressure_control_configuration.simulation_unit_id] = pressure_control_configuration

        return Solution(
            success=pressure_control_solution.success,
            configuration=list(configurations.values()),
        )
