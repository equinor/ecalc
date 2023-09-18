from __future__ import annotations

from datetime import datetime
from enum import Enum
from functools import partial
from typing import List, Optional

import numpy as np
from libecalc.common.logger import logger
from libecalc.common.string_utils import to_camel_case
from libecalc.common.units import Unit
from libecalc.dto import SingleSpeedChart, VariableSpeedChart
from pydantic import BaseModel
from pydantic.json import custom_pydantic_encoder


class EnergyModelBaseResult(BaseModel):
    class Config:
        alias_generator = to_camel_case
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ")}

    def json(self, date_format: Optional[str] = None, **kwargs) -> str:
        if date_format is None:
            return super().json(**kwargs)

        if kwargs.get("encoder") is None:
            # Override datetime encoder, use user specified date_format_option
            encoder = partial(
                custom_pydantic_encoder,
                {
                    datetime: lambda v: v.strftime(date_format),
                },
            )
        else:
            encoder = kwargs["encoder"]

        return super().json(**kwargs, encoder=encoder)

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
            elif isinstance(values, (Enum, str, dict, SingleSpeedChart, VariableSpeedChart)):
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

    energy_usage: List[Optional[float]]
    energy_usage_unit: Unit
    power: Optional[List[Optional[float]]]
    power_unit: Optional[Unit] = Unit.MEGA_WATT

    @property
    def is_valid(self) -> List[bool]:
        """We assume that all non-NaN results are valid calculation points except for a few exceptions where we override
        this method.
        """
        return list(~np.isnan(self.energy_usage))  # type: ignore[arg-type]

    @property
    def len(self) -> int:
        return len(self.energy_usage)
