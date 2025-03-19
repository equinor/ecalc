from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Self

from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import TimeSeries, TimeSeriesStreamDayRate


class EcalcResultBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def round_values(self, precisions=None):
        """Round the numeric values in the result to the specified precision."""
        RoundingUtils.round_values(self, precisions)

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


class RoundingUtils:
    @staticmethod
    def round_values(obj, precisions=None):
        """Round the numeric values in the result to the specified precision."""
        precisions = precisions or {}
        for key, value in vars(obj).items():
            precision = precisions.get(key)
            if precision is not None:
                if isinstance(value, TimeSeriesStreamDayRate):
                    RoundingUtils._round_timeseries(value, precision)
                elif isinstance(value, list):
                    setattr(obj, key, [RoundingUtils._round_nested(v, precision) for v in value])
                elif isinstance(value, (int | float)):
                    setattr(obj, key, RoundingUtils._round_decimal(value, precision))
                else:
                    setattr(obj, key, RoundingUtils._round_nested(value, precision))

    @staticmethod
    def _round_timeseries(timeseries, precision):
        """Round the numeric values in a TimeSeriesStreamDayRate object."""
        if hasattr(timeseries, "values") and isinstance(timeseries.values, list):
            timeseries.values = [
                RoundingUtils._round_decimal(v, precision) if isinstance(v, (int | float)) else v
                for v in timeseries.values
            ]

    @staticmethod
    def _round_nested(value, precision):
        """Recursively round numeric values in nested objects."""
        if isinstance(value, (int | float)):
            return RoundingUtils._round_decimal(value, precision)
        elif isinstance(value, list):
            return [RoundingUtils._round_nested(v, precision) for v in value]
        elif hasattr(value, "round_values"):
            value.round_values(precision)
            return value
        elif isinstance(value, TimeSeriesStreamDayRate):
            RoundingUtils._round_timeseries(value, precision)
            return value
        return value

    @staticmethod
    def _round_decimal(value, precision):
        """Round a numeric value using the decimal module."""
        quantize_str = "1." + "0" * precision
        rounded_value = float(Decimal(value).quantize(Decimal(quantize_str)).normalize())
        return rounded_value
