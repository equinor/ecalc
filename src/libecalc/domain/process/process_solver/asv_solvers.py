from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.entities.shaft.shaft import ShaftId
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import (
    UpstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.process_runner import Configuration, ProcessRunner
from libecalc.domain.process.process_solver.process_system_runner import ProcessSystemRunner
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import (
    ProcessSystem,
    ProcessSystemId,
    create_process_system_id,
)
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class ASVSolver:
    """
    Base class for solving ASV (Anti-Surge Valve) problems.

    Attributes:
        _shaft (Shaft): The shaft associated with the compressors.
        _compressors (list[CompressorStageProcessUnit]): List of compressor stage process units.
        _fluid_service (FluidService): The fluid service used in the process.
        _root_finding_strategy (ScipyRootFindingStrategy): Strategy for root finding.
    """

    def __init__(
        self,
        shaft: Shaft,
        compressors: list[CompressorStageProcessUnit],
        fluid_service: FluidService,
        individual_asv_control: bool = True,
        constant_pressure_ratio: bool = False,
        upstream_choke: Choke | None = None,
        downstream_choke: Choke | None = None,
    ) -> None:
        self._shaft = shaft
        self._compressors = compressors
        self._fluid_service = fluid_service
        self._root_finding_strategy = ScipyRootFindingStrategy()
        self._individual_asv_control = individual_asv_control
        self._constant_pressure_ratio = constant_pressure_ratio
        self._upstream_choke = upstream_choke
        self._downstream_choke = downstream_choke
        self._anti_surge_strategy: AntiSurgeStrategy
        self._recirculation_loops = (
            [
                RecirculationLoop(
                    process_system_id=create_process_system_id(),
                    inner_process=SerialProcessSystem(
                        process_system_id=create_process_system_id(),
                        propagators=[compressor],
                    ),
                    fluid_service=self._fluid_service,
                )
                for compressor in self._compressors
            ]
            if individual_asv_control
            else [
                RecirculationLoop(
                    process_system_id=create_process_system_id(),
                    inner_process=SerialProcessSystem(
                        process_system_id=create_process_system_id(),
                        propagators=self._compressors,
                    ),
                    fluid_service=self._fluid_service,
                )
            ]
        )
        recirculation_loop_ids = [recirculation_loop.get_id() for recirculation_loop in self._recirculation_loops]
        if upstream_choke is not None and downstream_choke is not None:
            raise ValueError("Only one of upstream_choke or downstream_choke can be set.")
        propagators: list[ProcessUnit | ProcessSystem]
        if downstream_choke is not None:
            propagators = [*self._recirculation_loops, downstream_choke]
        elif upstream_choke is not None:
            propagators = [upstream_choke, *self._recirculation_loops]
        else:
            propagators = [*self._recirculation_loops]

        self._simulator: ProcessRunner = ProcessSystemRunner(units=propagators, shaft=shaft)

        # TODO: send strategies for anti surge and pressure control via constructor
        # Anti surge strategy (always)
        if self._individual_asv_control:
            self._anti_surge_strategy = IndividualASVAntiSurgeStrategy(
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=self._compressors,
                simulator=self._simulator,
            )
        else:
            self._anti_surge_strategy = CommonASVAntiSurgeStrategy(
                recirculation_loop_id=recirculation_loop_ids[0],
                first_compressor=self._compressors[0],
                root_finding_strategy=self._root_finding_strategy,
                simulator=self._simulator,
            )

        # 2) Pressure control strategy (downstream choke if present, else ASV-based)

        if upstream_choke is not None:
            self._pressure_control_strategy = UpstreamChokePressureControlStrategy(
                simulator=self._simulator,
                choke_id=upstream_choke.get_id(),
                root_finding_strategy=self._root_finding_strategy,
            )
        elif downstream_choke is not None:
            self._pressure_control_strategy = DownstreamChokePressureControlStrategy(
                simulator=self._simulator,
                choke_id=downstream_choke.get_id(),
            )
        else:
            if self._individual_asv_control:
                if constant_pressure_ratio:
                    self._pressure_control_strategy = IndividualASVPressureControlStrategy(
                        simulator=self._simulator,
                        recirculation_loop_ids=recirculation_loop_ids,
                        compressors=self._compressors,
                        root_finding_strategy=self._root_finding_strategy,
                    )
                else:
                    self._pressure_control_strategy = IndividualASVRateControlStrategy(
                        simulator=self._simulator,
                        recirculation_loop_ids=recirculation_loop_ids,
                        compressors=self._compressors,
                    )
            else:
                self._pressure_control_strategy = CommonASVPressureControlStrategy(
                    simulator=self._simulator,
                    recirculation_loop_id=recirculation_loop_ids[0],
                    first_compressor=self._compressors[0],
                    root_finding_strategy=self._root_finding_strategy,
                )

        self._anti_surge_solution: Solution[list[Configuration[RecirculationConfiguration]]] | None = None

    def get_runner(self) -> ProcessRunner:
        return self._simulator

    def _get_initial_speed_boundary(self) -> Boundary:
        """
        Retrieve the initial speed boundary for the compressors.

        Returns:
            Boundary: The initial speed boundary.
        """
        speed_boundaries = [compressor.get_speed_boundary() for compressor in self._compressors]
        max_speed = max(speed_boundary.max for speed_boundary in speed_boundaries)
        min_speed = min(speed_boundary.min for speed_boundary in speed_boundaries)
        return Boundary(
            min=min_speed,
            max=max_speed,
        )

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
