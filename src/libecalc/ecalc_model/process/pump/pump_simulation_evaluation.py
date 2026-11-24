from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Self, assert_never

from libecalc.common.ddd import value_object
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import Period
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.ecalc_model.process.process_units import TimeSeriesPumpProcessUnit
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_pipeline_solver_builder import build_pump_pipeline_solver
from libecalc.ecalc_model.process.pump.pump_simulation import (
    PumpCommonStreamDistributionConfig,
    PumpIndividualStreamDistributionConfig,
    PumpProblem,
    PumpProblemId,
    PumpSimulation,
    PumpSimulationId,
    PumpStreamDistributionConfig,
)
from libecalc.ecalc_model.process.pump.time_series_liquid_stream import TimeSeriesLiquidStream
from libecalc.ecalc_model.validation import InvalidEcalcModelException, require_periods, require_unique
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessUnitConnectionId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_pressure_dropper import LiquidPressureDropper
from libecalc.process.pump.pump_solver.liquid_process_pipeline_runner import LiquidProcessPipelineRunner
from libecalc.process.pump.pump_solver.pump_pipeline_solver import PumpPipelineSolver
from libecalc.process.pump.pump_solver.pump_problem_solver import PumpProblemSolution
from libecalc.process.pump.stream_distribution.liquid_common_stream_distribution import LiquidCommonStreamDistribution
from libecalc.process.pump.stream_distribution.liquid_individual_stream_distribution import (
    LiquidIndividualStreamDistribution,
)
from libecalc.process.pump.stream_distribution.liquid_priorities_stream_distribution import (
    HasLiquidValidity,
    LiquidPrioritiesStreamDistribution,
)
from libecalc.process.pump.stream_distribution.liquid_stream_distribution import LiquidStreamDistribution
from libecalc.process.pump.stream_distribution.pump_stream_distribution_item import PumpStreamDistributionItem


@value_object
class PumpSimulationProblemResult:
    """The solution of one pump problem for one period, with the ids of the problem and its pump."""

    pump_problem_id: PumpProblemId
    pump_equipment_id: EquipmentId
    solution: PumpProblemSolution

    @property
    def is_valid(self) -> bool:
        return self.solution.is_valid


@value_object
class PumpSimulationPipelineResult:
    """The result of one pump pipeline for one period.

    ``problem_results`` is in flow order. ``connection_streams`` holds the stream on every connection of the
    pipeline.
    """

    pump_pipeline_id: ProcessPipelineId
    problem_results: Sequence[PumpSimulationProblemResult]
    connection_streams: Mapping[ProcessUnitConnectionId, LiquidStream]


@value_object
class PumpSimulationPeriodResult:
    """The selected setting for one period and the result of every pump pipeline under it.

    ``pipeline_results`` is in the order of ``PumpSimulation.get_pump_pipeline_ids()``.
    """

    period: Period
    selected_setting_index: int
    pipeline_results: Sequence[PumpSimulationPipelineResult]

    @property
    def is_valid(self) -> bool:
        return all(
            problem_result.is_valid
            for pipeline_result in self.pipeline_results
            for problem_result in pipeline_result.problem_results
        )


@value_object
class PumpSimulationResult:
    pump_simulation_id: PumpSimulationId
    period_results: Sequence[PumpSimulationPeriodResult]


def evaluate_pump_simulation(
    pump_simulation: PumpSimulation, pump_pipelines: Sequence[PumpPipeline]
) -> PumpSimulationResult:
    """Evaluate every pump pipeline of the simulation for every period.

    ``pump_pipelines`` holds at least the pipelines of the simulation, which has their ids.

    With a common stream, the setting of a period is the first one where every pump problem is valid, else
    the last one. With individual streams there is one setting. A pump outside its chart gives a flagged
    result, not an exception.
    """
    _reject_overflow(pump_simulation)
    pipelines = _get_pump_pipelines(pump_simulation, pump_pipelines)
    _reject_pump_in_several_pipelines(pump_simulation, pipelines)
    runtimes = [_PumpPipelineRuntime.build(pump_simulation, pipeline) for pipeline in pipelines]
    inlet = _read_stream_distribution(pump_simulation.get_stream_distribution())

    return PumpSimulationResult(
        pump_simulation_id=pump_simulation.get_id(),
        period_results=tuple(
            _evaluate_period(period, runtimes, inlet) for period in pump_simulation.get_process_periods()
        ),
    )


@dataclass(frozen=True, eq=False)
class _PumpPipelineRuntime:
    """The runtime of one pump pipeline and the values of its expressions by period.

    The solver, the runner and the pressure droppers are mutable, so an instance is equal to itself only.
    ``requested_outlet_pressures_bara`` has one entry per pump problem, in flow order.
    """

    pump_pipeline: PumpPipeline
    pump_problems: Sequence[PumpProblem]
    pump_equipment_ids: Mapping[ProcessUnitId, EquipmentId]
    solver: PumpPipelineSolver
    runner: LiquidProcessPipelineRunner
    pressure_droppers: Mapping[ProcessUnitId, LiquidPressureDropper]
    pressure_drop_bara: Mapping[ProcessUnitId, Mapping[Period, float]]
    requested_outlet_pressures_bara: Sequence[Mapping[Period, float]]

    @classmethod
    def build(cls, pump_simulation: PumpSimulation, pump_pipeline: PumpPipeline) -> Self:
        pump_problems = pump_simulation.get_pump_problems()[pump_pipeline.get_id()]
        solver, runner, pressure_droppers = build_pump_pipeline_solver(pump_pipeline, pump_problems)
        return cls(
            pump_pipeline=pump_pipeline,
            pump_problems=pump_problems,
            pump_equipment_ids={
                process_unit.get_id(): process_unit.pump_equipment_id
                for process_unit in pump_pipeline.get_process_units()
                if isinstance(process_unit, TimeSeriesPumpProcessUnit)
            },
            solver=solver,
            runner=runner,
            pressure_droppers=pressure_droppers,
            pressure_drop_bara=_read_pressure_drops(pump_simulation, pump_pipeline, pressure_droppers),
            requested_outlet_pressures_bara=[
                problem.get_constraint().outlet_pressure.get_masked_items() for problem in pump_problems
            ],
        )

    def set_pressure_drops(self, period: Period) -> None:
        for process_unit_id, pressure_drop_bara in self.pressure_drop_bara.items():
            self.pressure_droppers[process_unit_id].set_pressure_drop_bara(pressure_drop_bara[period])


class _PumpPipelineInPeriod(HasLiquidValidity):
    """One pump pipeline with its requested outlet pressures of one period.

    A pressure that is not positive while the pipeline is solved or run is raised with the pipeline and the
    period. A pressure drop can only be compared with the pressure of the stream that enters its pressure
    dropper, which after a pump is known when the pipeline is solved.
    """

    def __init__(self, runtime: _PumpPipelineRuntime, period: Period):
        self._runtime = runtime
        self._period = period
        self._item = PumpStreamDistributionItem(
            runtime.solver,
            requested_outlet_pressures_bara=[
                requested_outlet_pressure_bara[period]
                for requested_outlet_pressure_bara in runtime.requested_outlet_pressures_bara
            ],
        )

    def is_valid(self, inlet_stream: LiquidStream) -> bool:
        with self._located_non_positive_pressure():
            return self._item.is_valid(inlet_stream)

    def evaluate(self, inlet_stream: LiquidStream) -> PumpSimulationPipelineResult:
        runtime = self._runtime
        with self._located_non_positive_pressure():
            # The solutions are found first: the runner then holds the configuration of this stream.
            solutions = self._item.find_solutions(inlet_stream)
            stream_into_unit = runtime.runner.run_to_each_unit(inlet_stream)
        return PumpSimulationPipelineResult(
            pump_pipeline_id=runtime.pump_pipeline.get_id(),
            problem_results=tuple(
                PumpSimulationProblemResult(
                    pump_problem_id=problem.get_id(),
                    pump_equipment_id=runtime.pump_equipment_ids[solution.pump_result.process_unit_id],
                    solution=solution,
                )
                for problem, solution in zip(runtime.pump_problems, solutions, strict=True)
            ),
            connection_streams=MappingProxyType(
                {
                    connection.get_id(): stream_into_unit[connection.get_to_process_unit_id()]
                    for connection in runtime.pump_pipeline.get_process_unit_connections()
                }
            ),
        )

    @contextmanager
    def _located_non_positive_pressure(self) -> Iterator[None]:
        try:
            yield
        except NonPositivePressureException as error:
            raise InvalidEcalcModelException(
                f"Pump pipeline '{self._runtime.pump_pipeline.get_name()}' gets a pressure that is not positive "
                f"({error.pressure_bara} bara) in {self._period}. Check its pressure drops and its requested outlet "
                f"pressures."
            ) from error


@value_object
class _LiquidStreamValues:
    pressure_bara: Mapping[Period, float]
    density_kg_per_m3: Mapping[Period, float]
    volumetric_rate_m3_per_day: Mapping[Period, float]

    @classmethod
    def read(cls, stream: TimeSeriesLiquidStream) -> Self:
        rate = stream.volumetric_rate_m3_per_day
        return cls(
            pressure_bara=stream.pressure_bara.get_masked_items(),
            density_kg_per_m3=stream.density_kg_per_m3.get_masked_items(),
            volumetric_rate_m3_per_day=dict(zip(rate.get_periods().periods, rate.get_stream_day_values(), strict=True)),
        )

    def get_stream(self, period: Period) -> LiquidStream:
        return LiquidStream.from_volumetric_rate(
            volumetric_rate_m3_per_day=self.volumetric_rate_m3_per_day[period],
            pressure_bara=self.pressure_bara[period],
            density_kg_per_m3=self.density_kg_per_m3[period],
        )


@value_object
class _CommonInlet:
    """One inlet stream and its rate fractions, as ``rate_fractions_by_setting[setting][pipeline]``."""

    inlet_stream: _LiquidStreamValues
    rate_fractions_by_setting: Sequence[Sequence[Mapping[Period, float]]]

    def get_stream_distributions(self, period: Period) -> list[LiquidStreamDistribution]:
        inlet_stream = self.inlet_stream.get_stream(period)
        return [
            LiquidCommonStreamDistribution(
                inlet_stream=inlet_stream,
                rate_fractions=[rate_fraction[period] for rate_fraction in rate_fractions],
            )
            for rate_fractions in self.rate_fractions_by_setting
        ]


@value_object
class _IndividualInlets:
    """One inlet stream per pipeline, which is a single setting."""

    inlet_streams: Sequence[_LiquidStreamValues]

    def get_stream_distributions(self, period: Period) -> list[LiquidStreamDistribution]:
        return [
            LiquidIndividualStreamDistribution(
                streams=[inlet_stream.get_stream(period) for inlet_stream in self.inlet_streams]
            )
        ]


def _read_stream_distribution(stream_distribution: PumpStreamDistributionConfig) -> _CommonInlet | _IndividualInlets:
    match stream_distribution:
        case PumpCommonStreamDistributionConfig():
            return _CommonInlet(
                inlet_stream=_LiquidStreamValues.read(stream_distribution.inlet_stream),
                rate_fractions_by_setting=[
                    [rate_fraction.get_masked_items() for rate_fraction in setting.rate_fractions]
                    for setting in stream_distribution.settings
                ],
            )
        case PumpIndividualStreamDistributionConfig():
            return _IndividualInlets(
                inlet_streams=[
                    _LiquidStreamValues.read(inlet_stream) for inlet_stream in stream_distribution.inlet_streams
                ]
            )
        case _:
            assert_never(stream_distribution)


def _read_pressure_drops(
    pump_simulation: PumpSimulation,
    pump_pipeline: PumpPipeline,
    pressure_droppers: Mapping[ProcessUnitId, LiquidPressureDropper],
) -> dict[ProcessUnitId, dict[Period, float]]:
    subject = f"Pump pipeline '{pump_pipeline.get_name()}'"
    configurations = pump_simulation.get_process_configurations().get(pump_pipeline.get_id(), {})
    for process_unit_id in configurations:
        if process_unit_id not in pressure_droppers:
            raise ProgrammingError(
                f"{subject} has a process configuration for '{process_unit_id}', which is not a pressure dropper of "
                f"the pipeline, in the pump simulation '{pump_simulation.get_name()}'."
            )
    pressure_drop_bara_by_unit: dict[ProcessUnitId, dict[Period, float]] = {}
    for process_unit_id in pressure_droppers:
        configuration = configurations.get(process_unit_id)
        if configuration is None:
            raise ProgrammingError(
                f"{subject} has the pressure dropper '{process_unit_id}', which has no process configuration in "
                f"the pump simulation '{pump_simulation.get_name()}'."
            )
        pressure_drop = configuration.pressure_drop_in_bara
        require_periods(pressure_drop.get_periods(), pump_simulation.get_process_periods(), f"{subject} pressure drop")
        pressure_drop_bara_by_period = pressure_drop.get_masked_items()
        for period, pressure_drop_bara in pressure_drop_bara_by_period.items():
            if pressure_drop_bara < 0:
                raise InvalidEcalcModelException(
                    f"{subject} pressure drop [bara] must not be negative, got {pressure_drop_bara} in {period} "
                    f"for '{pressure_drop.get_original_expression()}'."
                )
        pressure_drop_bara_by_unit[process_unit_id] = pressure_drop_bara_by_period
    return pressure_drop_bara_by_unit


def _evaluate_period(
    period: Period, runtimes: Sequence[_PumpPipelineRuntime], inlet: _CommonInlet | _IndividualInlets
) -> PumpSimulationPeriodResult:
    for runtime in runtimes:
        runtime.set_pressure_drops(period)
    pipelines = [_PumpPipelineInPeriod(runtime, period) for runtime in runtimes]
    selected_setting_index, streams = LiquidPrioritiesStreamDistribution(
        stream_distributions=inlet.get_stream_distributions(period), items=pipelines
    ).select()

    return PumpSimulationPeriodResult(
        period=period,
        selected_setting_index=selected_setting_index,
        pipeline_results=tuple(pipeline.evaluate(stream) for pipeline, stream in zip(pipelines, streams, strict=True)),
    )


def _get_pump_pipelines(pump_simulation: PumpSimulation, pump_pipelines: Sequence[PumpPipeline]) -> list[PumpPipeline]:
    """The pump pipelines of the simulation, in the order of its pump pipeline ids."""
    pump_pipeline_by_id = {pump_pipeline.get_id(): pump_pipeline for pump_pipeline in pump_pipelines}
    missing_ids = [
        pump_pipeline_id
        for pump_pipeline_id in pump_simulation.get_pump_pipeline_ids()
        if pump_pipeline_id not in pump_pipeline_by_id
    ]
    if missing_ids:
        raise ProgrammingError(
            f"Pump simulation '{pump_simulation.get_name()}' refers to pump pipelines that are not given: "
            f"{', '.join(str(pump_pipeline_id) for pump_pipeline_id in missing_ids)}."
        )
    return [pump_pipeline_by_id[pump_pipeline_id] for pump_pipeline_id in pump_simulation.get_pump_pipeline_ids()]


def _reject_overflow(pump_simulation: PumpSimulation) -> None:
    stream_distribution = pump_simulation.get_stream_distribution()
    if isinstance(stream_distribution, PumpCommonStreamDistributionConfig) and any(
        setting.overflow for setting in stream_distribution.settings
    ):
        raise ProgrammingError(
            f"Pump simulation '{pump_simulation.get_name()}' has overflow between its pump pipelines, which is not "
            f"supported."
        )


def _reject_pump_in_several_pipelines(pump_simulation: PumpSimulation, pump_pipelines: Sequence[PumpPipeline]) -> None:
    require_unique(
        (
            process_unit.pump_equipment_id
            for pump_pipeline in pump_pipelines
            for process_unit in pump_pipeline.get_process_units()
            if isinstance(process_unit, TimeSeriesPumpProcessUnit)
        ),
        f"Pump simulation '{pump_simulation.get_name()}' pumps",
    )
