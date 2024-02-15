from __future__ import annotations

from pydantic import field_validator

from libecalc.common.math.numbers import Numbers
from libecalc.common.utils.rates import TimeSeries, TimeSeriesBoolean, TimeSeriesInt
from libecalc.dto.base import EcalcBaseModel


def control_maximum_decimals(v):
    """Control maximum number of decimals and convert null-floats to NaN."""
    if isinstance(v, TimeSeries) and not isinstance(v, (TimeSeriesInt, TimeSeriesBoolean)):
        return v.model_copy(
            update={
                "values": [
                    float(Numbers.format_to_precision(n, precision=6)) if n is not None else n for n in v.values
                ],
            }
        )

    if isinstance(v, list):
        return [control_maximum_decimals(x) for x in v]

    if isinstance(v, tuple):
        return [control_maximum_decimals(x) for x in v]

    if isinstance(v, float):
        if v.is_integer():
            return v

        return float(Numbers.format_to_precision(v, precision=6))

    return v


class EcalcResultBaseModel(EcalcBaseModel):
    # TODO: Think of a better way? Seems like a lot of unnecessary work, and it is probably not obvious that we are
    #   doing this at all in other places of the code.
    _pre_control_maximum_decimals = field_validator("*", mode="after")(control_maximum_decimals)
