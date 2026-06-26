from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.finders.recirculation_loop_rate_finder import RecirculationLoopRateFinder
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import Bisect, RootFindingStrategy
from libecalc.process.process_solver.solver import Solution
from libecalc.process.process_units.compressor import Compressor


class CommonASVPressureControlStrategy(PressureControlStrategy):
    """Varies a single recirculation rate across the entire train to meet target pressure.

    The strategy owns the compressor reference needed to compute the recirculation
    boundary at solve time, since boundary depends on speed which may not be set
    at construction time.
    """

    def __init__(
        self,
        simulator: ProcessRunner,
        recirculation_loop_id: ConfigurationHandlerId,
        first_compressor: Compressor,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._simulator = simulator
        self._recirculation_loop_id = recirculation_loop_id
        self._first_compressor = first_compressor
        self._root_finding_strategy = root_finding_strategy

    def reset(self) -> None:
        self._simulator.reset_configuration_handler(self._recirculation_loop_id)

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        self.reset()

        def recirculation_func(config: RecirculationConfiguration) -> FluidStream:
            self._simulator.apply_configuration(
                Configuration(configuration_handler_id=self._recirculation_loop_id, value=config)
            )
            return self._simulator.run(inlet_stream=inlet_stream)

        compressor_inlet_stream = self._simulator.run(inlet_stream=inlet_stream, to_id=self._first_compressor.get_id())
        boundary = self._first_compressor.get_recirculation_range(compressor_inlet_stream)

        finder = RecirculationLoopRateFinder(
            search_strategy=Bisect(tolerance=10e-3),
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )

        finding = finder.find(recirculation_func)
        return Solution(
            configuration=[
                Configuration(
                    configuration_handler_id=self._recirculation_loop_id,
                    value=finding.configuration,
                )
            ],
            failure=finding.failure,
        )
