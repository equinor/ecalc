from collections.abc import Mapping, Sequence
from typing import Final, NewType, Self, assert_never
from uuid import UUID

import networkx as nx

from libecalc.common.ddd import value_object
from libecalc.common.ddd.entity import Entity
from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.process.pump.time_series_liquid_stream import TimeSeriesLiquidStream
from libecalc.ecalc_model.time_series_configuration import TimeSeriesPressureDropperConfiguration
from libecalc.ecalc_model.validation import (
    InvalidEcalcModelException,
    require_name,
    require_periods,
    require_sequential_periods,
    require_unique,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessUnitConnectionId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.pump_process_simulation import PumpProcessSimulationId
from libecalc.process.stream_distribution.common_stream_distribution import Overflow

_RATE_FRACTION_TOLERANCE = 1e-9


@value_object
class PumpCommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow[ProcessPipelineId]]

    def __post_init__(self) -> None:
        if not self.rate_fractions:
            raise InvalidEcalcModelException("Pump common stream settings must have at least one rate fraction.")
        periods = self.rate_fractions[0].get_periods()
        for rate_fraction in self.rate_fractions:
            if rate_fraction.get_periods() != periods:
                raise InvalidEcalcModelException("Pump rate fractions must be defined for the same periods.")
        for period, fractions in zip(periods, zip(*self.get_rate_fraction_values(), strict=True), strict=True):
            if any(not 0 <= fraction <= 1 for fraction in fractions):
                raise InvalidEcalcModelException(
                    f"Pump rate fractions must be between 0 and 1, got {fractions} in {period}."
                )
            if sum(fractions) > 1 + _RATE_FRACTION_TOLERANCE:
                raise InvalidEcalcModelException(
                    f"Pump rate fractions must not sum to more than 1, got {sum(fractions)} in {period}."
                )

        overflow_graph: nx.DiGraph[ProcessPipelineId] = nx.DiGraph()
        for overflow in self.overflow:
            if overflow.from_id == overflow.to_id:
                raise InvalidEcalcModelException("Pump overflow must go to another pipeline than it comes from.")
            overflow_graph.add_edge(overflow.from_id, overflow.to_id)
        require_unique((overflow.from_id for overflow in self.overflow), "Pump overflow sources")
        if not nx.is_directed_acyclic_graph(overflow_graph):
            raise InvalidEcalcModelException("Pump overflow must not be cyclic.")

    def get_periods(self) -> list[Period]:
        return self.rate_fractions[0].get_periods()

    def get_rate_fraction_values(self) -> list[list[float]]:
        return [rate_fraction.get_masked_values() for rate_fraction in self.rate_fractions]


@value_object
class PumpCommonStreamDistributionConfig:
    inlet_stream: TimeSeriesLiquidStream
    settings: list[PumpCommonStreamSettings]

    def __post_init__(self) -> None:
        if not self.settings:
            raise InvalidEcalcModelException("Pump common stream distribution must have at least one setting.")
        number_of_rate_fractions = {len(setting.rate_fractions) for setting in self.settings}
        if len(number_of_rate_fractions) != 1:
            raise InvalidEcalcModelException(
                "Every pump common stream setting must have the same number of rate fractions."
            )
        for setting in self.settings:
            if setting.get_periods() != self.inlet_stream.get_periods():
                raise InvalidEcalcModelException(
                    "Pump rate fractions must be defined for the same periods as the inlet stream."
                )

    def get_number_of_streams(self) -> int:
        return len(self.settings[0].rate_fractions)


@value_object
class PumpIndividualStreamDistributionConfig:
    inlet_streams: list[TimeSeriesLiquidStream]

    def __post_init__(self) -> None:
        if not self.inlet_streams:
            raise InvalidEcalcModelException("Pump individual stream distribution must have at least one inlet stream.")
        periods = self.inlet_streams[0].get_periods()
        if any(inlet_stream.get_periods() != periods for inlet_stream in self.inlet_streams):
            raise InvalidEcalcModelException("Pump inlet streams must be defined for the same periods.")

    def get_number_of_streams(self) -> int:
        return len(self.inlet_streams)


type PumpStreamDistributionConfig = PumpCommonStreamDistributionConfig | PumpIndividualStreamDistributionConfig


@value_object
class PumpConstraint:
    outlet_pressure: TimeSeriesExpression
    target_process_unit_id: ProcessUnitId
    target_process_connection_id: ProcessUnitConnectionId


PumpProblemId = NewType("PumpProblemId", UUID)


class PumpProblem(Entity[PumpProblemId]):
    def __init__(
        self,
        constraint: PumpConstraint,
        pump_pipeline_id: ProcessPipelineId,
        choke_pressure_control_id: ProcessUnitId | None = None,
        pump_problem_id: PumpProblemId | None = None,
    ):
        self._constraint = constraint
        self._pump_pipeline_id = pump_pipeline_id
        self._choke_pressure_control_id = choke_pressure_control_id
        self._id: Final[PumpProblemId] = pump_problem_id or PumpProblem._create_id()

    def get_id(self) -> PumpProblemId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> PumpProblemId:
        return PumpProblemId(ecalc_id_generator())

    def get_constraint(self) -> PumpConstraint:
        return self._constraint

    def get_pump_pipeline_id(self) -> ProcessPipelineId:
        return self._pump_pipeline_id

    def get_choke_pressure_control_id(self) -> ProcessUnitId | None:
        return self._choke_pressure_control_id


type PumpProblems = Mapping[ProcessPipelineId, Sequence[PumpProblem]]


class PumpSimulation(Entity[PumpProcessSimulationId]):
    def __init__(
        self,
        name: str,
        stream_distribution: PumpStreamDistributionConfig,
        pump_problems: PumpProblems,
        process_periods: Sequence[Period],
        pump_simulation_id: PumpProcessSimulationId | None = None,
        process_configurations: Mapping[
            ProcessPipelineId, Mapping[ProcessUnitId, TimeSeriesPressureDropperConfiguration]
        ]
        | None = None,
    ):
        PumpSimulation._validate(name, stream_distribution, pump_problems, process_periods)
        process_configurations = process_configurations or {}
        PumpSimulation._validate_process_configurations(name, pump_problems, process_configurations)
        self._process_configurations = {
            pipeline_id: dict(configurations) for pipeline_id, configurations in process_configurations.items()
        }
        self._name = name
        self._stream_distribution = stream_distribution
        self._pump_problems = {pipeline_id: list(problems) for pipeline_id, problems in pump_problems.items()}
        self._process_periods = list(process_periods)
        self._id: Final[PumpProcessSimulationId] = pump_simulation_id or PumpSimulation._create_id()

    @staticmethod
    def _validate(
        name: str,
        stream_distribution: PumpStreamDistributionConfig,
        pump_problems: PumpProblems,
        process_periods: Sequence[Period],
    ) -> None:
        require_name(name, "Pump simulation")
        subject = f"Pump simulation '{name}'"
        require_sequential_periods(process_periods, subject)
        if not pump_problems:
            raise InvalidEcalcModelException(f"{subject} must have at least one pump pipeline.")
        pump_pipeline_ids = list(pump_problems)
        for pump_pipeline_id, problems in pump_problems.items():
            if not problems:
                raise InvalidEcalcModelException(
                    f"{subject} must have at least one pump problem for pump pipeline '{pump_pipeline_id}'."
                )
            for problem in problems:
                if problem.get_pump_pipeline_id() != pump_pipeline_id:
                    raise InvalidEcalcModelException(
                        f"{subject} pump problem '{problem.get_id()}' is for pump pipeline "
                        f"'{problem.get_pump_pipeline_id()}', but is given for pump pipeline '{pump_pipeline_id}'."
                    )
        all_problems = [problem for problems in pump_problems.values() for problem in problems]
        require_unique((problem.get_id() for problem in all_problems), f"{subject} pump problem ids")

        number_of_streams = stream_distribution.get_number_of_streams()
        if number_of_streams != len(pump_pipeline_ids):
            raise InvalidEcalcModelException(
                f"{subject} has {len(pump_pipeline_ids)} pump pipelines, but its stream distribution has "
                f"{number_of_streams} streams. Specify one stream per pump pipeline."
            )

        for problem in all_problems:
            require_periods(
                problem.get_constraint().outlet_pressure.get_periods(), process_periods, f"{subject} outlet pressure"
            )
        for inlet_stream in PumpSimulation._inlet_streams(stream_distribution):
            require_periods(inlet_stream.get_periods(), process_periods, f"{subject} inlet stream")

        if isinstance(stream_distribution, PumpCommonStreamDistributionConfig):
            for setting in stream_distribution.settings:
                for overflow in setting.overflow:
                    if overflow.from_id not in pump_pipeline_ids or overflow.to_id not in pump_pipeline_ids:
                        raise InvalidEcalcModelException(f"{subject} overflow must refer to its own pump pipelines.")

        for problems, may_run in zip(
            pump_problems.values(), PumpSimulation._may_run(stream_distribution, pump_pipeline_ids), strict=True
        ):
            for problem in problems:
                outlet_pressure = problem.get_constraint().outlet_pressure
                for period, value, running in zip(
                    process_periods, outlet_pressure.get_masked_values(), may_run, strict=True
                ):
                    if running and not value > 0:
                        raise InvalidEcalcModelException(
                            f"{subject} outlet pressure [bara] must be greater than 0 when the pump runs, got {value} "
                            f"in {period} for '{outlet_pressure.get_original_expression()}'."
                        )

    @staticmethod
    def _validate_process_configurations(
        name: str,
        pump_problems: PumpProblems,
        process_configurations: Mapping[
            ProcessPipelineId, Mapping[ProcessUnitId, TimeSeriesPressureDropperConfiguration]
        ],
    ) -> None:
        for pump_pipeline_id in process_configurations:
            if pump_pipeline_id not in pump_problems:
                raise InvalidEcalcModelException(
                    f"Pump simulation '{name}' has process configurations for pump pipeline '{pump_pipeline_id}', "
                    "which none of its pump problems simulate."
                )

    @staticmethod
    def _inlet_streams(stream_distribution: PumpStreamDistributionConfig) -> list[TimeSeriesLiquidStream]:
        match stream_distribution:
            case PumpCommonStreamDistributionConfig():
                return [stream_distribution.inlet_stream]
            case PumpIndividualStreamDistributionConfig():
                return list(stream_distribution.inlet_streams)
            case _:
                assert_never(stream_distribution)

    @staticmethod
    def _may_run(
        stream_distribution: PumpStreamDistributionConfig,
        pump_pipeline_ids: Sequence[ProcessPipelineId],
    ) -> list[list[bool]]:
        match stream_distribution:
            case PumpIndividualStreamDistributionConfig():
                return [
                    [rate > 0 for rate in inlet_stream.volumetric_rate_m3_per_day.get_stream_day_values()]
                    for inlet_stream in stream_distribution.inlet_streams
                ]
            case PumpCommonStreamDistributionConfig():
                inlet_rates = stream_distribution.inlet_stream.volumetric_rate_m3_per_day.get_stream_day_values()
                overflow_targets = {
                    overflow.to_id for setting in stream_distribution.settings for overflow in setting.overflow
                }
                fraction_values = [setting.get_rate_fraction_values() for setting in stream_distribution.settings]
                return [
                    [
                        inlet_rate > 0
                        and (
                            pump_pipeline_id in overflow_targets
                            or any(fractions[index][period] > 0 for fractions in fraction_values)
                        )
                        for period, inlet_rate in enumerate(inlet_rates)
                    ]
                    for index, pump_pipeline_id in enumerate(pump_pipeline_ids)
                ]
            case _:
                assert_never(stream_distribution)

    def get_id(self) -> PumpProcessSimulationId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> PumpProcessSimulationId:
        return PumpProcessSimulationId(ecalc_id_generator())

    def get_name(self) -> str:
        return self._name

    def get_stream_distribution(self) -> PumpStreamDistributionConfig:
        return self._stream_distribution

    def get_inlet_streams(self) -> list[TimeSeriesLiquidStream]:
        return PumpSimulation._inlet_streams(self._stream_distribution)

    def get_pump_pipeline_ids(self) -> list[ProcessPipelineId]:
        return list(self._pump_problems)

    def get_pump_problems(self) -> dict[ProcessPipelineId, list[PumpProblem]]:
        return {pipeline_id: list(problems) for pipeline_id, problems in self._pump_problems.items()}

    def get_process_periods(self) -> list[Period]:
        return list(self._process_periods)

    def get_process_configurations(
        self,
    ) -> dict[ProcessPipelineId, dict[ProcessUnitId, TimeSeriesPressureDropperConfiguration]]:
        return {
            pipeline_id: dict(configurations) for pipeline_id, configurations in self._process_configurations.items()
        }
