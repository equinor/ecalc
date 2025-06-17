from pydantic import BaseModel

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesValue


class TimeSeriesIntensity(BaseModel):
    periods: Periods
    values: list[TimeSeriesValue]
    unit: Unit
