from __future__ import annotations

from enum import Enum
from typing import Self

from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import TimeSeries
from libecalc.domain.process.core.results.rounding import round_values


class EcalcResultBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def round_values(value, precision=6):
        """Round the numeric values in the result to the specified precision."""
        return round_values(value, precision)

    def extend(self, other: Self) -> Self:
        """This is used when merging different time slots when the energy function of a consumer changes over time.
        Append method covering all the basics. All additional extend methods needs to be covered in
        the _append-method.
        """
        for attribute, values in self.__dict__.items():
            other_values = other.__getattribute__(attribute)

            if values is None or other_values is None:
                logger.warning(
                    f"Concatenating two temporal compressor results where result attribute '{attribute}' is undefined."
                )
            elif isinstance(values, Enum | str | dict | SingleSpeedChartDTO | VariableSpeedChartDTO):
                if values != other_values:
                    logger.warning(
                        f"Concatenating two temporal compressor model results where attribute {attribute} changes"
                        f" over time. The result is ambiguous and leads to loss of information."
                    )
            elif isinstance(values, EcalcResultBaseModel):
                # In case of nested models such as compressor with turbine
                values.extend(other_values)
            elif isinstance(values, list):
                if isinstance(other_values, list):
                    self.__setattr__(attribute, values + other_values)
                else:
                    self.__setattr__(attribute, values + [other_values])
            elif isinstance(values, TimeSeries):
                self.__setattr__(attribute, values.extend(other_values))
            elif isinstance(values, Periods):
                self.__setattr__(attribute, values + other_values)
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an extend strategy."
                    f"Please contact eCalc support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self
