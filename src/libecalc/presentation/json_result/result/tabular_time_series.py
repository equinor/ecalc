from abc import ABC
from datetime import datetime
from typing import Annotated, Self

import pandas as pd
from pydantic import TypeAdapter, WrapSerializer
from pydantic_core.core_schema import SerializationInfo

from libecalc.common.time_utils import Frequency, Periods, resample_periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeries,
    TimeSeriesBoolean,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.presentation.json_result.result.base import EcalcResultBaseModel


def with_timesteps(v: Periods, handler, info: SerializationInfo):
    context = info.context
    data = handler(v, info)
    if context:
        include_timesteps = context.get("include_timesteps", False)
        if include_timesteps:
            start_dates = v.start_dates
            type_adapter = TypeAdapter(list[datetime])
            if info.mode == "json":
                data["timesteps"] = type_adapter.dump_json(start_dates)
            else:
                data["timesteps"] = type_adapter.dump_python(start_dates)

    return data


PeriodsWithTimesteps = Annotated[Periods, WrapSerializer(with_timesteps)]


class TabularTimeSeries(ABC, EcalcResultBaseModel):
    name: str
    periods: PeriodsWithTimesteps

    def to_dataframe(
        self,
        prefix: str | None = None,
    ) -> pd.DataFrame:
        """
        Provide a dataframe representing the timeseries data in the object.

        TimeSeriesBoolean is converted into ints.

        Args:
            prefix: prefix for all column names

        Returns:

        """
        periods = self.periods
        df = pd.DataFrame(index=periods.start_dates)

        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, TimeSeries):
                unit_value = attribute_value.unit
                if isinstance(attribute_value, TimeSeriesRate):
                    unit_extension = "sd" if attribute_value.rate_type == RateType.STREAM_DAY else "cd"
                    if attribute_value.unit == Unit.MEGA_WATT:
                        unit_value = unit_value.replace(Unit.MEGA_WATT, f"{Unit.MEGA_WATT} ({unit_extension})")
                    else:
                        unit_value = unit_value.replace("/d", f"/{unit_extension}")
                elif isinstance(attribute_value, TimeSeriesVolumesCumulative):
                    unit_value = unit_value.replace(attribute_value.unit, f"{attribute_value.unit} (cd)")

                column_name = f"{attribute_name}[{unit_value}]"

                if isinstance(attribute_value, TimeSeriesBoolean):
                    values = [int(v) for v in attribute_value.values]
                else:
                    values = attribute_value.values

                timeseries_df = pd.DataFrame({column_name: values}, index=attribute_value.periods.start_dates)
                df = df.join(timeseries_df)
            elif isinstance(attribute_value, list):
                if len(attribute_value) > 0 and all(isinstance(item, TabularTimeSeries) for item in attribute_value):
                    for item in attribute_value:
                        tabular_df = item.to_dataframe(prefix=item.name)
                        df = df.join(tabular_df)

            elif (
                isinstance(attribute_value, dict)
                and len(attribute_value) > 0
                and all(isinstance(item, TabularTimeSeries) for item in attribute_value.values())
            ):
                for item in attribute_value.values():
                    tabular_df = item.to_dataframe(prefix=item.name)
                    df = df.join(tabular_df)

        if prefix is not None:
            df = df.add_prefix(prefix=f"{prefix}.")

        return df

    def resample(self, freq: Frequency) -> Self:
        """
        Immutable - returns a copy of itself

        Resample the given time series to the new Frequency given. Only data
        that is defined as a timeseries will be resampled.

        Args:
            freq: which frequency to resample to

        Returns: return a copy of itself with all data resampled to given frequency

        """
        if freq == freq.NONE:
            return self.model_copy()
        resampled = self.model_copy()
        for attribute, values in self.__dict__.items():
            if isinstance(values, TimeSeries) or isinstance(values, TabularTimeSeries):
                resampled.__setattr__(attribute, values.resample(freq=freq))

            elif isinstance(values, list):
                if len(values) > 0 and all(isinstance(item, TabularTimeSeries) for item in values):
                    resampled.__setattr__(attribute, [item.resample(freq) for item in values])

            elif isinstance(values, dict):
                if len(values) > 0 and all(isinstance(item, TabularTimeSeries) for item in values.values()):
                    resampled.__setattr__(attribute, {key: item.resample(freq) for key, item in values.items()})
                else:
                    # NOTE: Operational settings are not resampled. Should add support?
                    pass

            else:
                # NOTE: turbine_result is not resampled. Should add support?
                pass

        resampled.periods = resample_periods(self.periods, frequency=freq)
        return resampled
