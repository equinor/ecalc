from collections.abc import Sequence

from libecalc.common.ddd import value_object
from libecalc.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
    OperatingConfiguration,
    RecirculationConfiguration,
)
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump, PumpEvaluationResult
from libecalc.process.pump.pump_solver.liquid_choke_configuration_handler import LiquidChokeConfigurationHandler
from libecalc.process.pump.pump_solver.liquid_process_pipeline_runner import LiquidProcessPipelineRunner
from libecalc.process.pump.pump_solver.liquid_recirculation_loop import LiquidRecirculationLoop


@value_object
class PumpProblemSolution:
    """The result of the pump of one pump problem, and what reproduces it by propagation.

    ``configurations`` holds the recirculation rate [m3/h] and, when the problem has a choke, the choke
    pressure drop [bar]. The speed is ``pump_result.speed_rpm``, which is set on the pump with
    ``Pump.set_speed``.

    ``outlet_pressure_above_requested`` is true for a problem without a choke whose pump cannot run below
    the chart's minimum head at the operating rate: its operational discharge pressure is above the requested
    outlet pressure, nothing drops the difference, and the next unit gets the operational discharge pressure.
    The pump is within its chart, so the pump result is valid and the solution is not.
    """

    pump_result: PumpEvaluationResult
    configurations: Sequence[Configuration[OperatingConfiguration]]
    outlet_pressure_above_requested: bool

    @property
    def is_valid(self) -> bool:
        return self.pump_result.is_valid and not self.outlet_pressure_above_requested


class PumpProblemSolver:
    """Finds the configuration of one pump problem in closed form.

    ``Pump.evaluate`` gives the speed, the recirculation rate and the choke pressure drop, and the solver
    applies them to the units. Nothing is solved by iteration.

    The solver assumes that the pump is evaluated for the stream that enters its recirculation mixer, and
    that the units between the mixer and the problem's target are the pump, the splitter and, when the
    problem has one, the choke. The units upstream of the mixer have the configuration of their own
    problems, so the problems of a pipeline are solved in flow order.
    """

    def __init__(
        self,
        runner: LiquidProcessPipelineRunner,
        pump: Pump,
        recirculation_loop: LiquidRecirculationLoop,
        choke_configuration_handler: LiquidChokeConfigurationHandler | None,
    ):
        self._runner = runner
        self._pump = pump
        self._recirculation_loop = recirculation_loop
        self._choke_configuration_handler = choke_configuration_handler

    def find_solution(self, inlet_stream: LiquidStream, requested_outlet_pressure_bara: float) -> PumpProblemSolution:
        """Solve the problem for the stream at the inlet of the pipeline."""
        suction_stream = self._runner.run(inlet_stream, to_id=self._recirculation_loop.get_mixer_process_unit_id())
        pump_result = self._pump.evaluate(
            inlet_stream=suction_stream,
            requested_outlet_pressure_bara=requested_outlet_pressure_bara,
        )

        configurations: list[Configuration[OperatingConfiguration]] = [
            Configuration(
                configuration_handler_id=self._recirculation_loop.get_id(),
                value=RecirculationConfiguration(recirculation_rate=pump_result.recirculation_rate_m3_per_hour),
            )
        ]
        if self._choke_configuration_handler is not None:
            configurations.append(
                Configuration(
                    configuration_handler_id=self._choke_configuration_handler.get_id(),
                    value=ChokeConfiguration(delta_pressure=pump_result.choke_pressure_drop_bara),
                )
            )
        self._runner.apply_configurations(configurations)
        self._pump.set_speed(pump_result.speed_rpm)

        # The heads are compared, not the pressures: inside the chart the operational head is the required
        # head itself, while the discharge pressure is computed back from it.
        outlet_pressure_above_requested = (
            self._choke_configuration_handler is None
            and pump_result.speed_rpm is not None
            and pump_result.operational_head_joule_per_kg > pump_result.required_head_joule_per_kg
        )
        return PumpProblemSolution(
            pump_result=pump_result,
            configurations=tuple(configurations),
            outlet_pressure_above_requested=outlet_pressure_above_requested,
        )
