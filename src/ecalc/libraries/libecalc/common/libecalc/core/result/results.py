from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from libecalc.common.utils.rates import (
    TimeSeries,
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

    @property
    def _columns(self) -> Dict[str, Union[List, TimeSeries]]:
        """
        Returns: all attributes of a sequence type
        """
        columns = {}
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                columns[key] = value
            elif isinstance(value, TimeSeriesRate):
                columns[key] = value.values
                if value.regularity is not None:
                    columns[f"{key}_regularity"] = value.regularity
            elif isinstance(value, TimeSeries):
                columns[key] = value.values
        return columns

    @property
    def _dataframe(self) -> pd.DataFrame:
        """
        Returns: a dataframe of all sequence types
        """
        df = pd.DataFrame(self._columns)
        df.set_index(["timesteps"], inplace=True)
        df.index = pd.to_datetime(df.index)
        return df

    def _merge_columns(self, *other_compressor_results: CompressorResult) -> Dict[str, List]:
        """
        Merge all attributes of a sequence type.
        Args:
            *other_compressor_results:

        Returns:

        """
        df = pd.concat(
            [
                self._dataframe,
                *[other_compressor_result._dataframe for other_compressor_result in other_compressor_results],
            ],
            axis="index",
            verify_integrity=True,
        )
        df.sort_index(inplace=True)
        return {
            "timesteps": [timestamp.to_pydatetime() for timestamp in df.index.tolist()],
            **{str(key): list(value.values()) for key, value in df.to_dict().items()},
        }


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

    def merge(self, *other_compressor_results: CompressorResult) -> Self:
        """
        Merge all attributes of a sequence type, while also making sure the other attributes can be merged (i.e. id should be equal).
        Args:
            *other_compressor_results:

        Returns:

        """

        # Verify that the results are for the same consumer
        if len({self.id, *[other_compressor_result.id for other_compressor_result in other_compressor_results]}) != 1:
            raise ValueError("Can not merge results with differing ids.")

        # Verify units and rate types
        for key, value in self.__dict__.items():
            for other_compressor_result in other_compressor_results:
                other_value = other_compressor_result.__getattribute__(key)
                if isinstance(value, TimeSeriesRate):
                    if not isinstance(other_value, TimeSeriesRate):
                        raise ValueError(
                            f"Invalid type of {key} for compressor result with id {other_compressor_result.id}"
                        )
                    if value.rate_type != other_value.rate_type:
                        raise ValueError("Rate types does not match")

                if isinstance(value, TimeSeries):
                    if not isinstance(other_value, TimeSeries):
                        raise ValueError(
                            f"Invalid type of {key} for compressor result with id {other_compressor_result.id}"
                        )

                    if value.unit != other_value.unit:
                        raise ValueError("Units does not match")

        merged_columns = self._merge_columns(*other_compressor_results)
        timesteps = merged_columns.get("timesteps")

        return self.__class__(
            id=self.id,
            timesteps=timesteps,
            energy_usage=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("energy_usage"),
                unit=self.energy_usage.unit,
                regularity=merged_columns.get("energy_usage_regularity"),
                rate_type=self.energy_usage.rate_type,
            ),
            power=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("power"),
                unit=self.power.unit,
                regularity=merged_columns.get("power_regularity"),
                rate_type=self.power.rate_type,
            ),
            is_valid=TimeSeriesBoolean(
                timesteps=timesteps,
                values=merged_columns.get("is_valid"),
                unit=self.is_valid.unit,
            ),
            recirculation_loss=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("recirculation_loss"),
                unit=self.recirculation_loss.unit,
                regularity=merged_columns.get("recirculation_loss_regularity"),
                rate_type=self.recirculation_loss.rate_type,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                timesteps=timesteps,
                values=merged_columns.get("rate_exceeds_maximum"),
                unit=self.rate_exceeds_maximum.unit,
            ),
            outlet_pressure_before_choking=TimeSeriesFloat(
                timesteps=timesteps,
                values=merged_columns.get("outlet_pressure_before_choking"),
                unit=self.outlet_pressure_before_choking.unit,
            ),
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

    def merge(self, *other_compressor_results: CompressorResult) -> Self:
        """
        Merge all attributes of a sequence type, while also making sure the other attributes can be merged (i.e. id should be equal).
        Args:
            *other_compressor_results:

        Returns:

        """

        # Verify that the results are for the same consumer
        if len({self.id, *[other_compressor_result.id for other_compressor_result in other_compressor_results]}) == 1:
            raise ValueError("Can not merge results with differing ids.")

        # Verify units and rate types
        for key, value in self.__dict__.items():
            for other_compressor_result in other_compressor_results:
                other_value = other_compressor_result.__getattribute__(key)
                if isinstance(value, TimeSeriesRate):
                    if not isinstance(other_value, TimeSeriesRate):
                        raise ValueError(
                            f"Invalid type of {key} for compressor result with id {other_compressor_result.id}"
                        )
                    if value.typ != other_value.typ:
                        raise ValueError("Rate types does not match")

                if isinstance(value, TimeSeries):
                    if not isinstance(other_value, TimeSeries):
                        raise ValueError(
                            f"Invalid type of {key} for compressor result with id {other_compressor_result.id}"
                        )

                    if value.unit != other_value.unit:
                        raise ValueError("Units does not match")

        merged_columns = self._merge_columns(*other_compressor_results)
        timesteps = merged_columns.get("timesteps")

        return self.__class__(
            timesteps=timesteps,
            energy_usage=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("energy_usage"),
                unit=self.energy_usage.unit,
                regularity=merged_columns.get("energy_usage_regularity"),
                typ=self.energy_usage.typ,
            ),
            power=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("power"),
                unit=self.power.unit,
                regularity=merged_columns.get("power_regularity"),
                typ=self.energy_usage.typ,
            ),
            is_valid=TimeSeriesBoolean(
                timesteps=timesteps,
                values=merged_columns.get("is_valid"),
                unit=self.is_valid.unit,
            ),
            inlet_liquid_rate_m3_per_day=TimeSeriesRate(
                timesteps=timesteps,
                values=merged_columns.get("inlet_liquid_rate_m3_per_day"),
                unit=self.inlet_liquid_rate_m3_per_day.unit,
                regularity=merged_columns.get("inlet_liquid_rate_m3_per_day_regularity"),
                typ=self.inlet_liquid_rate_m3_per_day.typ,
            ),
            inlet_pressure_bar=TimeSeriesFloat(
                timesteps=timesteps,
                values=merged_columns.get("inlet_pressure_bar"),
                unit=self.inlet_pressure_bar.unit,
            ),
            outlet_pressure_bar=TimeSeriesFloat(
                timesteps=timesteps,
                values=merged_columns.get("outlet_pressure_bar"),
                unit=self.outlet_pressure_bar.unit,
            ),
            operational_head=TimeSeriesFloat(
                timesteps=timesteps,
                values=merged_columns.get("operational_head"),
                unit=self.operational_head.unit,
            ),
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
