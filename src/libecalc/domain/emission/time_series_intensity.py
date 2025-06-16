import math
from typing import Any

import pandas as pd
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesValue


class TimeSeriesIntensity(BaseModel):
    periods: Periods
    values: list[TimeSeriesValue]
    unit: Unit

    @field_validator("values", mode="before")
    @classmethod
    def convert_none_to_nan(cls, v: Any, info: ValidationInfo) -> list[TimeSeriesValue]:
        if isinstance(v, list):
            # convert None to nan
            return [i if i is not None else math.nan for i in v]  # type: ignore[misc]
        return v

    def to_dataframe(self, prefix: str = ""):
        col_name = prefix if prefix else "value"
        df = pd.DataFrame({col_name: self.values}, index=[p.start for p in self.periods])
        df.index.name = "period"
        return df
