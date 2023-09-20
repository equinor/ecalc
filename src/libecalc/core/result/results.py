from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from libecalc.common.tabular_time_series import TabularTimeSeriesUtils
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesRate,
)
from libecalc.core.models.results import CompressorTrainResult
from libecalc.core.result.base import EcalcResultBaseModel
from libecalc.dto.base import ComponentType
from typing_extensions import Self


class CommonResultBase(EcalcResultBaseModel):
    """Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc."""

    timesteps: List[datetime]
    is_valid: TimeSeriesBoolean

    # We need both energy usage and power rate since we sometimes want both fuel and power usage.
    energy_usage: TimeSeriesRate
    power: Optional[TimeSeriesRate]


class GenericComponentResult(CommonResultBase):
    id: str

    def merge(self, *other_results: CompressorResult) -> Self:
        """
        Merge all attributes of TimeSeries type, while also making sure the other attributes can be merged (i.e. id should be equal).
        Args:
            *other_results:

        Returns:

        """
        # Verify that we are merging the same entity
        if len({other_result.id for other_result in other_results}) != 1:
            raise ValueError("Can not merge objects with differing ids.")

        return TabularTimeSeriesUtils.merge(self, *other_results)


class GeneratorSetResult(GenericComponentResult):
    """The Generator set result component."""

    power_capacity_margin: TimeSeriesRate


class ConsumerSystemResult(GenericComponentResult):
    operational_settings_used: TimeSeriesInt
    operational_settings_results: Optional[Dict[int, List[Any]]]


class CompressorResult(GenericComponentResult):
    recirculation_loss: TimeSeriesRate
    rate_exceeds_maximum: TimeSeriesBoolean
    outlet_pressure_before_choking: TimeSeriesFloat

    def get_subset(self, indices: List[int]) -> Self:
        return self.__class__(
            id=self.id,
            timesteps=[self.timesteps[index] for index in indices],
            energy_usage=self.energy_usage[indices],
            is_valid=self.is_valid[indices],
            power=self.power[indices] if self.power is not None else None,
            recirculation_loss=self.recirculation_loss[indices],
            rate_exceeds_maximum=self.rate_exceeds_maximum[indices],
            outlet_pressure_before_choking=self.outlet_pressure_before_choking[indices],
        )


class PumpResult(GenericComponentResult):
    inlet_liquid_rate_m3_per_day: TimeSeriesRate
    inlet_pressure_bar: TimeSeriesFloat
    outlet_pressure_bar: TimeSeriesFloat
    operational_head: TimeSeriesFloat

    def get_subset(self, indices: List[int]) -> Self:
        return self.__class__(
            id=self.id,
            timesteps=[self.timesteps[index] for index in indices],
            energy_usage=self.energy_usage[indices],
            is_valid=self.is_valid[indices],
            power=self.power[indices] if self.power is not None else None,
            inlet_liquid_rate_m3_per_day=self.inlet_liquid_rate_m3_per_day[indices],
            inlet_pressure_bar=self.inlet_pressure_bar[indices],
            outlet_pressure_bar=self.outlet_pressure_bar[indices],
            operational_head=self.operational_head[indices],
        )


class ConsumerModelResultBase(ABC, CommonResultBase):
    """The Consumer base result component."""

    @property
    @abstractmethod
    def component_type(self):
        ...

    name: str


class PumpModelResult(ConsumerModelResultBase):
    """The Pump result component."""

    inlet_liquid_rate_m3_per_day: List[Optional[float]]
    inlet_pressure_bar: List[Optional[float]]
    outlet_pressure_bar: List[Optional[float]]
    operational_head: List[Optional[float]]

    @property
    def component_type(self):
        return ComponentType.PUMP


class CompressorModelResult(ConsumerModelResultBase, CompressorTrainResult):
    @property
    def component_type(self):
        return ComponentType.COMPRESSOR


class GenericModelResult(ConsumerModelResultBase):
    """Generic consumer result component."""

    @property
    def component_type(self):
        return ComponentType.GENERIC


# Consumer model result is referred to as ENERGY_USAGE_MODEL in the input YAML
ConsumerModelResult = Union[CompressorModelResult, PumpModelResult, GenericModelResult]

ComponentResult = Union[
    GeneratorSetResult,
    ConsumerSystemResult,
    CompressorResult,
    PumpResult,
    GenericComponentResult,
]  # Order is important as pydantic will parse results, so any result will be converted to the first fit in this list.


class EcalcModelResult(EcalcResultBaseModel):
    """Result object holding one component for each part of the eCalc model run."""

    component_result: ComponentResult
    sub_components: List[ComponentResult]
    models: List[ConsumerModelResult]
