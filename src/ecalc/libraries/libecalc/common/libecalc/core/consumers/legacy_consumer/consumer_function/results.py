from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import List, Literal, NamedTuple, Optional, Union

import numpy as np
from libecalc.common.logger import logger
from libecalc.core.consumers.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.core.models.results.base import EnergyFunctionResult
from pydantic import BaseModel


class ConditionsAndPowerLossResult(NamedTuple):
    condition: np.ndarray
    power_loss_factor: np.ndarray
    energy_usage_after_condition_before_power_loss_factor: np.ndarray
    resulting_energy_usage: np.ndarray
    resulting_power_usage: Optional[np.ndarray]


class ConsumerFunctionResultBase(BaseModel):
    """Result object for ConsumerFunction.

    Units:
        energy_usage [MW]
    """

    typ: ConsumerFunctionType

    time_vector: np.ndarray
    is_valid: np.ndarray
    energy_usage: np.ndarray
    energy_usage_before_conditioning: Optional[np.ndarray]
    energy_usage_before_power_loss_factor: Optional[np.ndarray]
    condition: Optional[np.ndarray]
    power_loss_factor: Optional[np.ndarray]
    energy_function_result: Optional[Union[EnergyFunctionResult, List[EnergyFunctionResult]]]

    # New! to support fuel to power rate...for e.g. compressors emulating turbine
    power: Optional[np.ndarray]

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def extend(self, other) -> ConsumerFunctionResultBase:
        ...


class ConsumerFunctionResult(ConsumerFunctionResultBase):
    typ: Literal[ConsumerFunctionType.SINGLE] = ConsumerFunctionType.SINGLE  # type: ignore[valid-type]

    def extend(self, other) -> ConsumerFunctionResult:
        if not isinstance(self, type(other)):
            msg = f"{self.__repr_name__()} Mixing CONSUMER_SYSTEM with non-CONSUMER_SYSTEM is no longer supported."
            logger.warning(msg)
            raise ValueError(msg)

        for attribute, values in self.__dict__.items():
            other_values = other.__getattribute__(attribute)

            if values is None or other_values is None or isinstance(values, Enum):
                continue
            elif isinstance(values, EnergyFunctionResult):
                if isinstance(values, type(other_values)):
                    values.extend(other_values)
                else:
                    # If the type does not match, then we convert to a list.
                    self.__setattr__(attribute, [values, other_values])
            elif isinstance(values, np.ndarray):
                self.__setattr__(attribute, np.append(values, other_values))
            elif isinstance(values, list):
                if isinstance(other_values, list):
                    values.extend(other_values)
                else:
                    values.append(other_values)
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an append method."
                    f" You should not land here. Please contact the eCalc Support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self

    @classmethod
    def create_empty(cls) -> ConsumerFunctionResult:
        return cls(time_vector=np.array([]), is_valid=np.array([]), energy_usage=np.array([]))
