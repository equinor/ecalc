from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.stream_distribution.common_stream_distribution import Overflow
from libecalc.domain.process.value_objects.fluid_stream.time_series_stream import TimeSeriesStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass
class CommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow]


@dataclass
class CommonStreamDistributionConfig:
    inlet_stream: TimeSeriesStream
    settings: list[CommonStreamSettings]


@dataclass
class IndividualStreamDistributionConfig:
    inlet_streams: list[TimeSeriesStream]


@dataclass
class Constraint:
    process_system_id: ProcessSystemId
    outlet_pressure: TimeSeriesExpression


@dataclass
class PressureControlConfig:
    process_system_id: ProcessSystemId
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]


@dataclass
class AntiSurgeConfig:
    process_system_id: ProcessSystemId
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]


@dataclass
class ProcessSimulation:
    process_systems: list[ProcessSystem]
    pressure_control_strategies: list[PressureControlConfig]
    anti_surge_strategies: list[AntiSurgeConfig]
    constraints: list[Constraint]
    stream_distribution: IndividualStreamDistributionConfig | CommonStreamDistributionConfig
from abc import ABC, abstractmethod

from libecalc.domain.process.process_system.process_system import ProcessSystem


class ProcessSimulation(ABC):

    @abstractmethod
    def get_process_systems(self) -> list[ProcessSystem]: ...