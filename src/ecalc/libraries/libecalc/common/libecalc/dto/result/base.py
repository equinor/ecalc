from __future__ import annotations

from libecalc.common.numbers import Numbers
from libecalc.common.utils.rates import TimeSeries, TimeSeriesInt
from libecalc.dto.base import EcalcBaseModel
from pydantic import validator


def control_maximum_decimals(v):
    """Control maximum number of decimals and convert null-floats to NaN."""
    if isinstance(v, TimeSeries) and not isinstance(v, TimeSeriesInt):
        return v.copy(
            update={
                "values": [
                    float(Numbers.format_to_precision(n, precision=6)) if n is not None else n for n in v.values
                ],
            }
        )

    if isinstance(v, float):
        if v.is_integer():
            return v

        return float(Numbers.format_to_precision(v, precision=6))

    return v


class EcalcResultBaseModel(EcalcBaseModel):
    _pre_control_maximum_decimals = validator("*", pre=False, each_item=True, allow_reuse=True)(
        control_maximum_decimals
    )
