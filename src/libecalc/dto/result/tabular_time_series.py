from abc import ABC
from datetime import datetime
from typing import List, Optional

import pandas as pd
from libecalc.common.time_utils import Frequency
from libecalc.common.utils.rates import TimeSeries, TimeSeriesBoolean
from libecalc.dto.result.base import EcalcResultBaseModel
from typing_extensions import Self


class TabularTimeSeries(ABC, EcalcResultBaseModel):
    name: str
    timesteps: List[datetime]

    def to_dataframe(
        self,
        prefix: Optional[str] = None,
    ) -> pd.DataFrame:
        timesteps = self.timesteps
        df = pd.DataFrame(index=timesteps)

        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, TimeSeries):
                column_name = f"{attribute_name}[{attribute_value.unit}]"

                if isinstance(attribute_value, TimeSeriesBoolean):
                    values = [int(v) for v in attribute_value.values]
                else:
                    values = attribute_value.values

                timeseries_df = pd.DataFrame({column_name: values}, index=attribute_value.timesteps)
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
            return self.copy()
        resampled = self.copy()
        for attribute, values in self.__dict__.items():
            if isinstance(values, TimeSeries):
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

        resampled.timesteps = (
            pd.date_range(start=self.timesteps[0], end=self.timesteps[-1], freq=freq.value).to_pydatetime().tolist()
        )
        return resampled
