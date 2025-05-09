from __future__ import annotations

import copy
from abc import abstractmethod
from enum import Enum
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.domain.process.core.results.base import EnergyFunctionResult
from libecalc.presentation.yaml.validation_errors import Location


class ConsumerFunctionResultBase:
    """Result object for ConsumerFunction.

    Units:
        energy_usage [MW]
    """

    def __init__(
        self,
        typ: ConsumerFunctionType,
        periods: Periods,
        is_valid: NDArray,
        energy_usage: NDArray,
        energy_usage_before_power_loss_factor: NDArray | None = None,
        condition: NDArray | None = None,
        power_loss_factor: NDArray | None = None,
        energy_function_result: EnergyFunctionResult | list[EnergyFunctionResult] | None = None,
        # New! to support fuel to power rate...for e.g. compressors emulating turbine
        power: NDArray | None = None,
    ):
        self.typ = typ
        self.periods = periods
        self.is_valid = is_valid
        self.energy_usage = energy_usage
        self.energy_usage_before_power_loss_factor = energy_usage_before_power_loss_factor
        self.condition = condition
        self.power_loss_factor = power_loss_factor
        self.energy_function_result = energy_function_result
        self.power = power

    @abstractmethod
    def extend(self, other: object) -> ConsumerFunctionResultBase: ...

    def model_copy(self, deep: bool = False) -> ConsumerFunctionResultBase:
        if deep:
            return copy.deepcopy(self)
        return copy.copy(self)


class ConsumerFunctionResult(ConsumerFunctionResultBase):
    def __init__(
        self,
        periods: Periods,
        is_valid: NDArray,
        energy_usage: NDArray,
        typ: Literal[ConsumerFunctionType.SINGLE] = ConsumerFunctionType.SINGLE,  # type: ignore[valid-type]
        energy_usage_before_power_loss_factor: NDArray | None = None,
        condition: NDArray | None = None,
        power_loss_factor: NDArray | None = None,
        energy_function_result: EnergyFunctionResult | list[EnergyFunctionResult] | None = None,
        power: NDArray | None = None,
    ):
        super().__init__(
            typ,
            periods,
            is_valid,
            energy_usage,
            energy_usage_before_power_loss_factor,
            condition,
            power_loss_factor,
            energy_function_result,
            power,
        )
        self.typ = typ
        self.periods = periods
        self.is_valid = is_valid
        self.energy_usage = energy_usage
        self.energy_usage_before_power_loss_factor = energy_usage_before_power_loss_factor
        self.condition = condition
        self.power_loss_factor = power_loss_factor
        self.energy_function_result = energy_function_result
        self.power = power

    def extend(self, other) -> ConsumerFunctionResult:
        """This is used when merging different time slots when the energy function of a consumer changes over time."""
        if not isinstance(self, type(other)):
            msg = "Mixing CONSUMER_SYSTEM with non-CONSUMER_SYSTEM is no longer supported."
            logger.warning(msg)
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.__repr_name__(),
                        message=msg,
                        location=Location([self.__repr_name__()]),  # for now, we will use the name as the location
                    )
                ]
            )

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
            elif isinstance(values, Periods):
                self.__setattr__(attribute, values + other_values)
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
        """Create empty consumer function result"""
        return cls(periods=Periods([]), is_valid=np.array([]), energy_usage=np.array([]))
