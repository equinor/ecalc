from collections.abc import Callable

from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.gas_compressor import GasCompressor
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
    DownstreamChokeRunner,
)
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import (
    UpstreamChokePressureControlStrategy,
    UpstreamChokeRunner,
)
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import create_process_system_id
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class ASVSolver:
    """
    Solver for Anti-Surge Valve (ASV) and shaft-speed problems.

    Accepts a flat list of individual ProcessUnit objects. GasCompressor units are
    automatically wrapped in per-compressor RecirculationLoops for individual ASV
    control, or in a single loop for common ASV. Conditioning units
    (TemperatureSetter, LiquidRemover, Choke, etc.) remain outside loops.
    """

    def __init__(
        self,
        shaft: Shaft,
        process_items: list[ProcessUnit],
        fluid_service: FluidService,
        individual_asv_control: bool = True,
        constant_pressure_ratio: bool = False,
        upstream_choke: Choke | None = None,
        downstream_choke: Choke | None = None,
    ) -> None:
        self._shaft = shaft
        self._fluid_service = fluid_service
        self._root_finding_strategy = ScipyRootFindingStrategy()
        self._individual_asv_control = individual_asv_control
        self._constant_pressure_ratio = constant_pressure_ratio
        self._upstream_choke = upstream_choke
        self._downstream_choke = downstream_choke
        self._anti_surge_strategy: AntiSurgeStrategy

        self._gas_compressors: list[GasCompressor] = [u for u in process_items if isinstance(u, GasCompressor)]
        if not self._gas_compressors:
            raise ValueError("process_items must contain at least one GasCompressor.")

        if upstream_choke is not None and downstream_choke is not None:
            raise ValueError("Only one of upstream_choke or downstream_choke can be set.")

        if individual_asv_control:
            # Build one RecirculationLoop per GasCompressor.
            compressor_to_loop: dict[int, RecirculationLoop] = {}
            for compressor in self._gas_compressors:
                loop = RecirculationLoop(
                    process_system_id=create_process_system_id(),
                    inner_process=SerialProcessSystem(
                        process_system_id=create_process_system_id(),
                        propagators=[compressor],
                    ),
                    fluid_service=self._fluid_service,
                )
                compressor_to_loop[id(compressor)] = loop

            self._recirculation_loops: list[RecirculationLoop] = list(compressor_to_loop.values())

            # Replace each GasCompressor in process_items with its loop; keep all other units in place.
            self._full_propagation_chain: list[ProcessUnit | RecirculationLoop] = [
                compressor_to_loop[id(unit)] if isinstance(unit, GasCompressor) else unit for unit in process_items
            ]

            self._anti_surge_strategy = IndividualASVAntiSurgeStrategy(
                propagation_chain=self._full_propagation_chain,
                recirculation_loops=self._recirculation_loops,
            )

            if constant_pressure_ratio:
                self._pressure_control_strategy = IndividualASVPressureControlStrategy(
                    propagation_chain=self._full_propagation_chain,
                    recirculation_loops=self._recirculation_loops,
                    gas_compressors=self._gas_compressors,
                    root_finding_strategy=self._root_finding_strategy,
                )
            else:
                self._pressure_control_strategy = IndividualASVRateControlStrategy(
                    propagation_chain=self._full_propagation_chain,
                    recirculation_loops=self._recirculation_loops,
                    gas_compressors=self._gas_compressors,
                )
        else:
            # Common ASV: one big RecirculationLoop around ALL process units.
            common_loop = RecirculationLoop(
                process_system_id=create_process_system_id(),
                inner_process=SerialProcessSystem(
                    process_system_id=create_process_system_id(),
                    propagators=process_items,
                ),
                fluid_service=self._fluid_service,
            )
            self._recirculation_loops = [common_loop]
            self._full_propagation_chain = [common_loop]

            self._anti_surge_strategy = CommonASVAntiSurgeStrategy(
                recirculation_loop=common_loop,
                first_compressor=self._gas_compressors[0],
                root_finding_strategy=self._root_finding_strategy,
            )

            if upstream_choke is not None:
                upstream_choke_process_system = SerialProcessSystem(
                    process_system_id=create_process_system_id(),
                    propagators=[upstream_choke, common_loop],
                )
                self._pressure_control_strategy = UpstreamChokePressureControlStrategy(
                    runner=UpstreamChokeRunner(
                        process_system=upstream_choke_process_system,
                        upstream_choke=upstream_choke,
                    ),
                    root_finding_strategy=self._root_finding_strategy,
                )
            elif downstream_choke is not None:
                downstream_choke_process_system = SerialProcessSystem(
                    process_system_id=create_process_system_id(),
                    propagators=[common_loop, downstream_choke],
                )
                self._pressure_control_strategy = DownstreamChokePressureControlStrategy(
                    runner=DownstreamChokeRunner(
                        process_system=downstream_choke_process_system,
                        downstream_choke=downstream_choke,
                    ),
                )
            else:
                self._pressure_control_strategy = CommonASVPressureControlStrategy(
                    recirculation_loop=common_loop,
                    first_compressor=self._gas_compressors[0],
                    root_finding_strategy=self._root_finding_strategy,
                )

    def get_initial_speed_boundary(self) -> Boundary:
        """Retrieve the shaft speed boundary from the compressor charts."""
        speed_boundaries = [compressor.get_speed_boundary() for compressor in self._gas_compressors]
        return Boundary(
            min=min(b.min for b in speed_boundaries),
            max=max(b.max for b in speed_boundaries),
        )

    def get_recirculation_solver(
        self,
        boundary: Boundary,
        target_pressure: FloatConstraint | None = None,
    ) -> RecirculationSolver:
        return RecirculationSolver(
            root_finding_strategy=self._root_finding_strategy,
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )

    def get_recirculation_loops(self) -> list[RecirculationLoop]:
        return self._recirculation_loops

    def get_recirculation_loop(self, loop_number: int = 0) -> RecirculationLoop:
        assert loop_number < len(
            self._recirculation_loops
        ), "Loop number exceeds the number of available recirculation loops."
        return self._recirculation_loops[loop_number]

    def propagate_stream_with_no_recirculation(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for item in self._full_propagation_chain:
            if isinstance(item, RecirculationLoop):
                item.set_recirculation_rate(0)
            current_stream = item.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def _propagate_for_speed_search(self, inlet_stream: FluidStream) -> FluidStream:
        return self.propagate_stream_with_no_recirculation(inlet_stream=inlet_stream)

    def get_recirculation_func(
        self, inlet_stream: FluidStream, loop_number: int = 0
    ) -> Callable[[RecirculationConfiguration], FluidStream]:
        def recirculation_func(configuration: RecirculationConfiguration) -> FluidStream:
            recirculation_loop = self.get_recirculation_loop(loop_number)
            recirculation_loop.set_recirculation_rate(configuration.recirculation_rate)
            current_stream = inlet_stream
            for item in self._full_propagation_chain:
                current_stream = item.propagate_stream(inlet_stream=current_stream)
            return current_stream

        return recirculation_func

    def get_recirculation_rate_solutions(self, success: bool = True) -> list[Solution[RecirculationConfiguration]]:
        return [
            Solution(
                success=success,
                configuration=RecirculationConfiguration(
                    recirculation_rate=recirculation_loop.get_recirculation_rate()
                ),
            )
            for recirculation_loop in self._recirculation_loops
        ]

    def _build_asv_result(
        self,
        speed_solution: Solution[SpeedConfiguration],
        success: bool,
    ) -> tuple[Solution[SpeedConfiguration], list[Solution[RecirculationConfiguration]]]:
        return speed_solution, self.get_recirculation_rate_solutions(success=success)

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> tuple[Solution[SpeedConfiguration], FluidStream]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            try:
                self._shaft.set_speed(configuration.speed)
                return self._propagate_for_speed_search(inlet_stream=inlet_stream)
            except RateTooLowError:
                # Reset anti-surge control state before applying the strategy.
                self._anti_surge_strategy.reset()
                return self._anti_surge_strategy.apply(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)

        # Ensure system is configured to chosen speed and return the outlet stream at that speed
        outlet_at_chosen_speed = speed_func(speed_solution.configuration)
        return speed_solution, outlet_at_chosen_speed

    def find_asv_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> tuple[Solution[SpeedConfiguration], list[Solution[RecirculationConfiguration]]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        speed_solution, outlet_at_chosen_speed = self._find_speed_solution(
            pressure_constraint=pressure_constraint, inlet_stream=inlet_stream
        )

        if speed_solution.success and outlet_at_chosen_speed.pressure_bara == pressure_constraint:
            # Speed solver found a valid solution where natural outlet equals the target.
            return self._build_asv_result(speed_solution=speed_solution, success=True)

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            # Pressure control (ASV/choke) can only reduce outlet pressure. If we're already below
            # target at the chosen speed, no pressure control can help.
            return self._build_asv_result(speed_solution=speed_solution, success=False)

        success = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )
        return self._build_asv_result(speed_solution=speed_solution, success=success)
