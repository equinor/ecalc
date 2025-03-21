from __future__ import annotations

from enum import Enum

import numpy as np

from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.units import Unit
from libecalc.domain.process.core.results.rounding import round_values


class EnergyModelBaseResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def round_values(value, precision=6):
        """Round the numeric values in the result to the specified precision."""
        return round_values(value, precision)

    def extend(self, other: EnergyModelBaseResult) -> EnergyModelBaseResult:
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
            elif isinstance(values, EnergyModelBaseResult):
                # In case of nested models such as compressor with turbine
                values.extend(other_values)
            elif isinstance(values, list):
                if isinstance(other_values, list):
                    self.__setattr__(attribute, values + other_values)
                else:
                    self.__setattr__(attribute, values + [other_values])
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an extend strategy."
                    f"Please contact eCalc support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self


class EnergyFunctionResult(EnergyModelBaseResult):
    """energy_usage: Energy usage values [MW] or [Sm3/day]
    power: Power in MW if applicable.
    """

    def __init__(
        self,
        energy_usage: list[float | None],
        energy_usage_unit: Unit,
        power: list[float | None] | None = None,
        power_unit: Unit | None = Unit.MEGA_WATT,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.energy_usage = energy_usage
        self.energy_usage_unit = energy_usage_unit
        self.power = power
        self.power_unit = power_unit

    @property
    def is_valid(self) -> list[bool]:
        """We assume that all non-NaN results are valid calculation points except for a few exceptions where we override
        this method.
        """
        return list(~np.isnan(self.energy_usage))  # type: ignore[arg-type]

    @property
    def len(self) -> int:
        return len(self.energy_usage)
